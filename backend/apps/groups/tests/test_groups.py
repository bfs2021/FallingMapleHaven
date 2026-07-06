import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.chat.models import ChatRoom, ChatRoomMember
from apps.feed.models import Post
from apps.groups.models import GroupJoinRequest, GroupMember, InterestGroup
from apps.notifications.models import Notification

User = get_user_model()

GROUP_URL = "/api/v1/groups/"


# ── Helpers ─────────────────────────────────────────────────────

def _url(*parts):
    parts_str = "/".join(str(p) for p in parts)
    return f"/api/v1/groups/{parts_str}/"


def _create_post(author, group):
    return Post.objects.create(author=author, group=group, content="Test post")


# ── GroupListView ───────────────────────────────────────────────

class TestGroupListView:
    def test_list_shows_all_groups_for_authenticated(self, alice_client, test_group, private_group):
        resp = alice_client.get(GROUP_URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        ids = {g["id"] for g in data}
        assert test_group.id in ids
        assert private_group.id in ids

    def test_list_anonymous_only_public(self, client, test_group, private_group):
        resp = client.get(GROUP_URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        ids = {g["id"] for g in data}
        assert test_group.id in ids
        assert private_group.id not in ids

    def test_list_member_count(self, alice_client, test_group, group_member):
        resp = alice_client.get(GROUP_URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        group_data = next(g for g in data if g["id"] == test_group.id)
        assert group_data["member_count"] == 2

    def test_list_is_member_flag(self, bob_client, test_group, group_member, private_group):
        resp = bob_client.get(GROUP_URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        for g in data:
            if g["id"] == test_group.id:
                assert g["is_member"] is True
            if g["id"] == private_group.id:
                assert g["is_member"] is False

    def test_list_empty(self, client, db):
        resp = client.get(GROUP_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["data"] == []


# ── GroupCreateView ─────────────────────────────────────────────

class TestGroupCreateView:
    def test_create_group_success(self, alice_client):
        resp = alice_client.post(_url("create"), {"name": "New Group"})
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()["data"]
        assert data["name"] == "New Group"
        group = InterestGroup.objects.get(pk=data["id"])
        assert group.creator == alice_client.handler._force_user
        assert GroupMember.objects.filter(group=group, user=group.creator, role="admin").exists()
        assert ChatRoom.objects.filter(group=group, room_type=ChatRoom.Type.GROUP, is_group=True).exists()

    def test_create_group_missing_name(self, alice_client):
        resp = alice_client.post(_url("create"), {"description": "no name"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_group_unauthenticated(self, client, db):
        resp = client.post(_url("create"), {"name": "New Group"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── GroupDetailView ─────────────────────────────────────────────

class TestGroupDetailView:
    def test_detail_member_sees_full(self, bob_client, test_group, group_member):
        resp = bob_client.get(_url(test_group.id))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert data["id"] == test_group.id
        assert data["is_member"] is True
        assert len(data["members"]) == 2
        assert data["owner"]["user_id"] == test_group.creator.id

    def test_detail_non_member_sees_basic(self, charlie_client, test_group):
        resp = charlie_client.get(_url(test_group.id))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert data["id"] == test_group.id
        assert data["is_member"] is False

    def test_detail_non_existent(self, alice_client):
        resp = alice_client.get(_url(99999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["code"] == 40004

    def test_detail_unauthenticated(self, client, test_group):
        resp = client.get(_url(test_group.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── GroupUpdateView ─────────────────────────────────────────────

class TestGroupUpdateView:
    def test_update_creator_can_update(self, alice_client, test_group):
        resp = alice_client.patch(_url(test_group.id, "update"), {"name": "Updated"})
        assert resp.status_code == status.HTTP_200_OK
        test_group.refresh_from_db()
        assert test_group.name == "Updated"

    def test_update_non_creator_cannot(self, bob_client, test_group, group_member):
        resp = bob_client.patch(_url(test_group.id, "update"), {"name": "Hacked"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update_non_existent(self, alice_client):
        resp = alice_client.patch(_url(99999, "update"), {"name": "x"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_update_unauthenticated(self, client, test_group):
        resp = client.patch(_url(test_group.id, "update"), {"name": "x"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update_set_private(self, alice_client, test_group):
        resp = alice_client.patch(_url(test_group.id, "update"), {"is_public": False})
        assert resp.status_code == status.HTTP_200_OK
        test_group.refresh_from_db()
        assert test_group.is_public is False


# ── GroupJoinView ───────────────────────────────────────────────

class TestGroupJoinView:
    def test_join_public_group_success(self, charlie_client, test_group):
        resp = charlie_client.post(_url(test_group.id, "join"))
        assert resp.status_code == status.HTTP_200_OK
        assert GroupMember.objects.filter(group=test_group, user=charlie_client.handler._force_user).exists()

        room = ChatRoom.objects.filter(group=test_group).first()
        if room:
            assert ChatRoomMember.objects.filter(room=room, user=charlie_client.handler._force_user).exists()

    def test_join_public_group_idempotent(self, bob_client, test_group, group_member):
        resp = bob_client.post(_url(test_group.id, "join"))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert GroupMember.objects.filter(group=test_group, user=bob_client.handler._force_user).count() == 1

    def test_join_private_group_creates_request(self, bob_client, private_group):
        resp = bob_client.post(_url(private_group.id, "join"))
        assert resp.status_code == status.HTTP_200_OK
        assert GroupJoinRequest.objects.filter(
            group=private_group, applicant=bob_client.handler._force_user, status=GroupJoinRequest.Status.PENDING
        ).exists()
        assert Notification.objects.filter(
            notification_type=Notification.Type.GROUP_JOIN_REQUEST,
            recipient=private_group.creator,
        ).exists()

    def test_join_private_group_idempotent(self, bob_client, private_group):
        bob = bob_client.handler._force_user
        GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        resp = bob_client.post(_url(private_group.id, "join"))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_join_non_existent(self, alice_client):
        resp = alice_client.post(_url(99999, "join"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_join_unauthenticated(self, client, test_group):
        resp = client.post(_url(test_group.id, "join"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── GroupLeaveView ──────────────────────────────────────────────

class TestGroupLeaveView:
    def test_leave_success(self, bob_client, test_group, group_member):
        bob = bob_client.handler._force_user
        resp = bob_client.post(_url(test_group.id, "leave"))
        assert resp.status_code == status.HTTP_200_OK
        assert not GroupMember.objects.filter(group=test_group, user=bob).exists()

        room = ChatRoom.objects.filter(group=test_group).first()
        if room:
            assert not ChatRoomMember.objects.filter(room=room, user=bob).exists()

    def test_leave_creator_cannot(self, alice_client, test_group):
        resp = alice_client.post(_url(test_group.id, "leave"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_leave_non_member(self, charlie_client, test_group):
        resp = charlie_client.post(_url(test_group.id, "leave"))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_leave_unauthenticated(self, client, test_group):
        resp = client.post(_url(test_group.id, "leave"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── GroupMemberManageView ───────────────────────────────────────

class TestGroupMemberManageView:
    def test_remove_member(self, alice_client, test_group, group_member):
        bob = group_member.user
        resp = alice_client.post(
            _url(test_group.id, "members", bob.id),
            {"action": "remove"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert not GroupMember.objects.filter(group=test_group, user=bob).exists()

    def test_promote_to_admin(self, alice_client, test_group, group_member):
        bob = group_member.user
        resp = alice_client.post(
            _url(test_group.id, "members", bob.id),
            {"action": "promote_admin"},
        )
        assert resp.status_code == status.HTTP_200_OK
        group_member.refresh_from_db()
        assert group_member.role == "admin"

    def test_demote_admin_to_member(self, alice_client, test_group, group_member):
        bob = group_member.user
        group_member.role = "admin"
        group_member.save()
        resp = alice_client.post(
            _url(test_group.id, "members", bob.id),
            {"action": "demote_admin"},
        )
        assert resp.status_code == status.HTTP_200_OK
        group_member.refresh_from_db()
        assert group_member.role == "member"

    def test_non_admin_cannot_manage(self, bob_client, test_group, group_member, charlie):
        charlie = User.objects.create_user(username="charlie2", password="Pass1234!", nickname="Charlie2")
        GroupMember.objects.create(group=test_group, user=charlie, role="member")
        resp = bob_client.post(
            _url(test_group.id, "members", charlie.id),
            {"action": "remove"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_manage_creator(self, alice_client, test_group, group_member):
        resp = alice_client.post(
            _url(test_group.id, "members", test_group.creator.id),
            {"action": "remove"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_action(self, alice_client, test_group, group_member):
        bob = group_member.user
        resp = alice_client.post(
            _url(test_group.id, "members", bob.id),
            {"action": "invalid"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_existent_user(self, alice_client, test_group):
        resp = alice_client.post(
            _url(test_group.id, "members", 99999),
            {"action": "remove"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_non_existent_group(self, alice_client):
        resp = alice_client.post(
            _url(99999, "members", 1),
            {"action": "remove"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_only_owner_can_remove_admin(self, alice_client, test_group, group_member):
        bob = group_member.user
        group_member.role = "admin"
        group_member.save()

        charlie = User.objects.create_user(username="charlie3", password="Pass1234!", nickname="Charlie3")
        GroupMember.objects.create(group=test_group, user=charlie, role="admin")

        charlie_client_ = type(alice_client)()
        charlie_client_.force_authenticate(user=charlie)

        resp = charlie_client_.post(
            _url(test_group.id, "members", bob.id),
            {"action": "remove"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_only_owner_can_promote_demote_admin(self, alice_client, test_group, group_member):
        bob = group_member.user
        charlie = User.objects.create_user(username="charlie4", password="Pass1234!", nickname="Charlie4")
        GroupMember.objects.create(group=test_group, user=charlie, role="admin")
        charlie_client_ = type(alice_client)()
        charlie_client_.force_authenticate(user=charlie)

        resp = charlie_client_.post(
            _url(test_group.id, "members", bob.id),
            {"action": "promote_admin"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── GroupPostsView ──────────────────────────────────────────────

class TestGroupPostsView:
    def test_member_can_see_posts(self, bob_client, test_group, group_member):
        post = _create_post(author=test_group.creator, group=test_group)
        resp = bob_client.get(_url(test_group.id, "posts"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["results"][0]["id"] == post.id

    def test_non_member_cannot_see(self, charlie_client, test_group):
        _create_post(author=test_group.creator, group=test_group)
        resp = charlie_client.get(_url(test_group.id, "posts"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_empty_posts(self, bob_client, test_group, group_member):
        resp = bob_client.get(_url(test_group.id, "posts"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["results"] == []

    def test_non_existent_group(self, alice_client):
        resp = alice_client.get(_url(99999, "posts"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── GroupDeleteView ─────────────────────────────────────────────

class TestGroupDeleteView:
    def test_creator_delete_success(self, alice_client, test_group, group_member):
        group_id = test_group.id
        resp = alice_client.post(_url(group_id, "delete"))
        assert resp.status_code == status.HTTP_200_OK
        assert not InterestGroup.objects.filter(pk=group_id).exists()
        assert not GroupMember.objects.filter(group_id=group_id).exists()
        assert not ChatRoom.objects.filter(group_id=group_id).exists()

    def test_staff_cannot_delete_unless_owner(self, staff_client, test_group, group_member):
        """Staff who is not the creator/member cannot delete (no staff bypass in current code)."""
        resp = staff_client.post(_url(test_group.id, "delete"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_non_creator_cannot_delete(self, bob_client, test_group, group_member):
        resp = bob_client.post(_url(test_group.id, "delete"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_non_existent(self, alice_client):
        resp = alice_client.post(_url(99999, "delete"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_cascades_posts(self, alice_client, test_group):
        post = _create_post(author=test_group.creator, group=test_group)
        resp = alice_client.post(_url(test_group.id, "delete"))
        assert resp.status_code == status.HTTP_200_OK
        post.refresh_from_db()
        assert post.group is None


# ── GroupTransferView ───────────────────────────────────────────

class TestGroupTransferView:
    def test_transfer_success(self, alice_client, test_group, group_member):
        bob = group_member.user
        resp = alice_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": bob.id},
        )
        assert resp.status_code == status.HTTP_200_OK
        test_group.refresh_from_db()
        assert test_group.creator == bob

    def test_old_creator_becomes_member(self, alice_client, test_group, group_member):
        alice = test_group.creator
        bob = group_member.user
        alice_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": bob.id},
        )
        membership = GroupMember.objects.get(group=test_group, user=alice)
        assert membership.role == "member"

    def test_new_owner_becomes_admin(self, alice_client, test_group, group_member):
        bob = group_member.user
        alice_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": bob.id},
        )
        membership = GroupMember.objects.get(group=test_group, user=bob)
        assert membership.role == "admin"

    def test_transfer_to_non_member(self, alice_client, test_group, charlie):
        resp = alice_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": charlie.id},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_creator_cannot_transfer(self, bob_client, test_group, group_member):
        resp = bob_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": test_group.creator.id},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_transfer_to_self(self, alice_client, test_group):
        resp = alice_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": test_group.creator.id},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_new_owner_id(self, alice_client, test_group):
        resp = alice_client.post(_url(test_group.id, "transfer"), {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_new_owner_id_does_not_crash(self, alice_client, test_group):
        resp = alice_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": "abc"},
        )
        assert resp.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_transfer_syncs_chatroom(self, alice_client, test_group, group_member):
        bob = group_member.user
        room = ChatRoom.objects.create(
            name=test_group.name, room_type=ChatRoom.Type.GROUP, group=test_group
        )
        ChatRoomMember.objects.create(room=room, user=test_group.creator)
        resp = alice_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": bob.id},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert ChatRoomMember.objects.filter(room=room, user=bob).exists()

    def test_transfer_chatroom_idempotent(self, alice_client, test_group, group_member):
        bob = group_member.user
        room = ChatRoom.objects.create(
            name=test_group.name, room_type=ChatRoom.Type.GROUP, group=test_group
        )
        ChatRoomMember.objects.create(room=room, user=test_group.creator)
        ChatRoomMember.objects.create(room=room, user=bob)
        resp = alice_client.post(
            _url(test_group.id, "transfer"),
            {"new_owner_id": bob.id},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert ChatRoomMember.objects.filter(room=room, user=bob).count() == 1


# ── GroupJoinRequestListView ────────────────────────────────────

class TestGroupJoinRequestListView:
    def test_admin_can_see_pending_requests(self, alice_client, private_group, bob):
        req = GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        resp = alice_client.get(_url(private_group.id, "join-requests"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == req.id

    def test_non_admin_cannot_see(self, bob_client, private_group, bob):
        resp = bob_client.get(_url(private_group.id, "join-requests"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_empty_requests(self, alice_client, test_group):
        resp = alice_client.get(_url(test_group.id, "join-requests"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["data"] == []

    def test_non_existent_group(self, alice_client):
        resp = alice_client.get(_url(99999, "join-requests"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_only_pending_requests_shown(self, alice_client, private_group, bob, charlie):
        GroupJoinRequest.objects.create(group=private_group, applicant=bob, status=GroupJoinRequest.Status.PENDING)
        GroupJoinRequest.objects.create(group=private_group, applicant=charlie, status=GroupJoinRequest.Status.APPROVED)
        resp = alice_client.get(_url(private_group.id, "join-requests"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["data"]) == 1


# ── GroupJoinRequestHandleView ──────────────────────────────────

class TestGroupJoinRequestHandleView:
    def test_approve_creates_member(self, alice_client, private_group, bob):
        req = GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        resp = alice_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "approved"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert GroupMember.objects.filter(group=private_group, user=bob).exists()
        req.refresh_from_db()
        assert req.status == GroupJoinRequest.Status.APPROVED

    def test_approve_idempotent(self, alice_client, private_group, bob):
        req = GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        GroupMember.objects.create(group=private_group, user=bob)
        resp = alice_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "approved"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert GroupMember.objects.filter(group=private_group, user=bob).count() == 1

    def test_approve_adds_to_chatroom(self, alice_client, private_group, bob):
        room = ChatRoom.objects.create(
            name=private_group.name, room_type=ChatRoom.Type.GROUP, group=private_group
        )
        ChatRoomMember.objects.create(room=room, user=private_group.creator)
        req = GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        resp = alice_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "approved"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert ChatRoomMember.objects.filter(room=room, user=bob).exists()

    def test_reject_success(self, alice_client, private_group, bob):
        req = GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        resp = alice_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "rejected"},
        )
        assert resp.status_code == status.HTTP_200_OK
        req.refresh_from_db()
        assert req.status == GroupJoinRequest.Status.REJECTED
        assert not GroupMember.objects.filter(group=private_group, user=bob).exists()

    def test_reject_creates_notification(self, alice_client, private_group, bob):
        req = GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        resp = alice_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "rejected"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(
            notification_type=Notification.Type.GROUP_REQUEST_REJECTED,
            recipient=bob,
        ).exists()

    def test_non_admin_cannot_handle(self, bob_client, private_group, bob, charlie):
        req = GroupJoinRequest.objects.create(group=private_group, applicant=charlie)
        resp = bob_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "approved"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_already_handled(self, alice_client, private_group, bob):
        req = GroupJoinRequest.objects.create(
            group=private_group, applicant=bob, status=GroupJoinRequest.Status.APPROVED
        )
        resp = alice_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "approved"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_action(self, alice_client, private_group, bob):
        req = GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        resp = alice_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "invalid"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_existent_request(self, alice_client, private_group):
        resp = alice_client.post(
            _url(private_group.id, "join-requests", 99999, "handle"),
            {"action": "approved"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_non_existent_group(self, alice_client):
        resp = alice_client.post(
            _url(99999, "join-requests", 1, "handle"),
            {"action": "approved"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_handled_by_is_set(self, alice_client, private_group, bob):
        alice = alice_client.handler._force_user
        req = GroupJoinRequest.objects.create(group=private_group, applicant=bob)
        alice_client.post(
            _url(private_group.id, "join-requests", req.id, "handle"),
            {"action": "approved"},
        )
        req.refresh_from_db()
        assert req.handled_by == alice
        assert req.handled_at is not None


# ── Concurrency / Idempotency ───────────────────────────────────

class TestGroupIdempotency:
    def test_direct_join_get_or_create(self, db):
        alice = User.objects.create_user(username="ida_alice", password="Pass1234!", nickname="IDA Alice")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=True)
        member, created = GroupMember.objects.get_or_create(group=group, user=alice)
        assert created is True
        member, created = GroupMember.objects.get_or_create(group=group, user=alice)
        assert created is False
        assert GroupMember.objects.filter(group=group, user=alice).count() == 1

    def test_approve_join_get_or_create(self, db):
        alice = User.objects.create_user(username="ida_alice2", password="Pass1234!", nickname="IDA Alice2")
        bob = User.objects.create_user(username="ida_bob", password="Pass1234!", nickname="IDA Bob")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=False)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        GroupJoinRequest.objects.create(group=group, applicant=bob)
        member, created = GroupMember.objects.get_or_create(group=group, user=bob)
        assert created is True
        member, created = GroupMember.objects.get_or_create(group=group, user=bob)
        assert created is False
        assert GroupMember.objects.filter(group=group, user=bob).count() == 1
