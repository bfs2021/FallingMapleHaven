import pytest
from rest_framework import status

BASE = "/api/v1/groups/"

pytestmark = pytest.mark.django_db


class TestCreateGroup:
    """POST /groups/create/ — PRD §2.6"""

    def test_create_group_success(self, alice_client, alice):
        resp = alice_client.post(
            BASE + "create/",
            {"name": "New Group", "description": "A test group", "is_public": True},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data.get("data", {})
        assert data["name"] == "New Group"
        assert data["is_public"] is True

    def test_create_group_requires_auth(self, client):
        resp = client.post(
            BASE + "create/",
            {"name": "No Auth Group", "description": "", "is_public": True},
            format="multipart",
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_create_group_with_cover_image(self, alice_client, fake_image):
        resp = alice_client.post(
            BASE + "create/",
            {
                "name": "Cover Group",
                "description": "With cover",
                "is_public": True,
                "cover_image": fake_image,
            },
            format="multipart",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data.get("data", {})
        assert data["cover_url"] is not None


class TestListGroups:
    """GET /groups/ — PRD §2.6"""

    def test_list_contains_created_group(self, alice_client, test_group):
        resp = alice_client.get(BASE)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", [])
        ids = [g["id"] for g in data]
        assert test_group.id in ids

    def test_list_shows_public_groups_to_anon(self, client, test_group):
        resp = client.get(BASE)
        assert resp.status_code == status.HTTP_200_OK
        ids = [g["id"] for g in resp.data.get("data", [])]
        assert test_group.id in ids

    def test_list_hides_private_from_anon(self, client, private_group):
        resp = client.get(BASE)
        ids = [g["id"] for g in resp.data.get("data", [])]
        assert private_group.id not in ids

    def test_list_shows_is_member_flag(self, alice_client, test_group, group_member):
        resp = alice_client.get(BASE)
        data = resp.data.get("data", [])
        for g in data:
            if g["id"] == test_group.id:
                assert g["is_member"] is True
                break
        else:
            pytest.fail("test_group not in list")


class TestGroupDetail:
    """GET /groups/{id}/ — PRD §2.6"""

    def test_detail_has_members_and_metadata(self, alice_client, test_group):
        resp = alice_client.get(BASE + f"{test_group.id}/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", {})
        assert data["id"] == test_group.id
        assert data["name"] == test_group.name
        assert data["owner"]["user_id"] == test_group.creator.id
        assert len(data["members"]) >= 1
        assert data["member_count"] >= 1
        assert "created_at" in data

    def test_detail_requires_auth(self, client, test_group):
        resp = client.get(BASE + f"{test_group.id}/")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_detail_nonexistent_group(self, alice_client):
        resp = alice_client.get(BASE + "99999/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestJoinPublicGroup:
    """POST /groups/{id}/join/ — PRD §2.6"""

    def test_join_public_group(self, charlie_client, charlie, test_group):
        resp = charlie_client.post(BASE + f"{test_group.id}/join/")
        assert resp.status_code == status.HTTP_200_OK
        assert test_group.members.filter(user=charlie).exists()

    def test_join_private_group_creates_request(self, charlie_client, charlie, private_group):
        resp = charlie_client.post(BASE + f"{private_group.id}/join/")
        assert resp.status_code == status.HTTP_200_OK
        from apps.groups.models import GroupJoinRequest
        assert GroupJoinRequest.objects.filter(
            group=private_group, applicant=charlie, status="pending"
        ).exists()

    def test_join_duplicate_member(self, alice_client, test_group):
        resp = alice_client.post(BASE + f"{test_group.id}/join/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_join_requires_auth(self, client, test_group):
        resp = client.post(BASE + f"{test_group.id}/join/")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestLeaveGroup:
    """POST /groups/{id}/leave/ — PRD §2.6"""

    def test_leave_group(self, bob_client, bob, test_group, group_member):
        resp = bob_client.post(BASE + f"{test_group.id}/leave/")
        assert resp.status_code == status.HTTP_200_OK
        assert not test_group.members.filter(user=bob).exists()

    def test_creator_cannot_leave(self, alice_client, test_group):
        resp = alice_client.post(BASE + f"{test_group.id}/leave/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_leave_non_member(self, charlie_client, test_group):
        resp = charlie_client.post(BASE + f"{test_group.id}/leave/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestRemoveMember:
    """POST /groups/{id}/members/{user_id}/ with action=remove — PRD §2.6"""

    def test_creator_remove_member(self, alice_client, test_group, group_member):
        bob_id = group_member.user.id
        resp = alice_client.post(
            BASE + f"{test_group.id}/members/{bob_id}/",
            {"action": "remove"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert not test_group.members.filter(user_id=bob_id).exists()

    def test_remove_requires_auth(self, client, test_group, group_member):
        resp = client.post(
            BASE + f"{test_group.id}/members/{group_member.user.id}/",
            {"action": "remove"},
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestTransferOwnership:
    """POST /groups/{id}/transfer/ — PRD §2.6"""

    def test_transfer_success(self, alice_client, test_group, group_member):
        bob_id = group_member.user.id
        resp = alice_client.post(
            BASE + f"{test_group.id}/transfer/",
            {"new_owner_id": bob_id},
        )
        assert resp.status_code == status.HTTP_200_OK
        test_group.refresh_from_db()
        assert test_group.creator.id == bob_id

    def test_transfer_updates_role(self, alice_client, alice, test_group, group_member):
        bob_id = group_member.user.id
        alice_client.post(
            BASE + f"{test_group.id}/transfer/",
            {"new_owner_id": bob_id},
        )
        from apps.groups.models import GroupMember
        old_owner_membership = GroupMember.objects.get(group=test_group, user=alice)
        assert old_owner_membership.role == "member"
        new_owner_membership = GroupMember.objects.get(group=test_group, user_id=bob_id)
        assert new_owner_membership.role == "admin"

    def test_transfer_requires_owner(self, bob_client, test_group, group_member):
        resp = bob_client.post(
            BASE + f"{test_group.id}/transfer/",
            {"new_owner_id": group_member.user.id},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestGroupPosts:
    """GET /groups/{id}/posts/ — PRD §2.6"""

    def test_list_group_posts(self, alice_client, alice, test_group):
        from apps.feed.models import Post
        post = Post.objects.create(author=alice, content="Group post", group=test_group)
        resp = alice_client.get(BASE + f"{test_group.id}/posts/", {"page": 1, "page_size": 20})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", {})
        assert data["total"] >= 1
        results = data.get("results", [])
        result_ids = [r["id"] for r in results]
        assert post.id in result_ids

    def test_group_posts_requires_membership(self, charlie_client, test_group):
        resp = charlie_client.get(BASE + f"{test_group.id}/posts/", {"page": 1})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_group_posts_requires_auth(self, client, test_group):
        resp = client.get(BASE + f"{test_group.id}/posts/", {"page": 1})
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestDeleteGroup:
    """POST /groups/{id}/delete/ — PRD §2.6"""

    def test_creator_can_delete(self, alice_client, test_group):
        resp = alice_client.post(BASE + f"{test_group.id}/delete/")
        assert resp.status_code == status.HTTP_200_OK

    def test_non_creator_cannot_delete(self, bob_client, test_group, group_member):
        resp = bob_client.post(BASE + f"{test_group.id}/delete/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_requires_auth(self, client, test_group):
        resp = client.post(BASE + f"{test_group.id}/delete/")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestUpdateGroup:
    """PATCH /groups/{id}/update/ — PRD §2.6"""

    def test_update_group_info(self, alice_client, test_group):
        resp = alice_client.patch(
            BASE + f"{test_group.id}/update/",
            {"name": "Updated Group", "description": "Updated desc"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_200_OK
        test_group.refresh_from_db()
        assert test_group.name == "Updated Group"
        assert test_group.description == "Updated desc"

    def test_update_toggle_public(self, alice_client, test_group):
        resp = alice_client.patch(
            BASE + f"{test_group.id}/update/",
            {"is_public": False},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_200_OK
        test_group.refresh_from_db()
        assert test_group.is_public is False

    def test_non_creator_cannot_update(self, bob_client, test_group, group_member):
        resp = bob_client.patch(
            BASE + f"{test_group.id}/update/",
            {"name": "Hacked"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update_requires_auth(self, client, test_group):
        resp = client.patch(
            BASE + f"{test_group.id}/update/",
            {"name": "No Auth"},
            format="multipart",
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )