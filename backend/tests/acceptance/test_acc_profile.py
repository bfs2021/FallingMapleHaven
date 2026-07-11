import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.profiles.models import GuestbookEntry, UserProfile, VisitRecord

User = get_user_model()

BASE = "/api/v1/profiles/"

pytestmark = pytest.mark.django_db


class TestGetProfile:
    """GET /profiles/{username_or_id}/ — PRD §2.5"""

    def test_own_profile_friend_status_self(self, alice_client, alice):
        resp = alice_client.get(BASE + f"{alice.username}/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["friend_status"] == "self"
        assert data["user_id"] == alice.id

    def test_friend_profile_friend_status_accepted(
        self, alice_client, bob, friendship
    ):
        resp = alice_client.get(BASE + f"{bob.username}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["friend_status"] == "accepted"

    def test_stranger_profile_friend_status_none(self, alice_client, charlie):
        resp = alice_client.get(BASE + f"{charlie.username}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["friend_status"] == "none"

    def test_anonymous_can_view_profile(self, client, alice):
        resp = client.get(BASE + f"{alice.username}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["friend_status"] == "none"

    def test_profile_response_has_expected_fields(self, alice_client, alice):
        resp = alice_client.get(BASE + f"{alice.username}/")
        data = resp.data["data"]
        expected = {
            "user_id", "nickname", "avatar_url", "cover_url", "bio",
            "real_name", "show_real_name", "date_joined", "visitor_count",
            "visitor_public", "layout_config", "friend_status", "plugins",
        }
        assert expected - set(data.keys()) == set()

    def test_profile_not_found(self, alice_client):
        resp = alice_client.get(BASE + "nonexistent_user/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestProfilePathParam:
    """Profile supports both username string and numeric ID as path param"""

    def test_get_by_username(self, alice_client, alice):
        resp = alice_client.get(BASE + f"{alice.username}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["user_id"] == alice.id

    def test_get_by_numeric_id(self, alice_client, alice):
        resp = alice_client.get(BASE + f"{alice.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["user_id"] == alice.id


class TestProfilePosts:
    """GET /profiles/{username_or_id}/posts/ — PRD §2.5.2"""

    def test_returns_own_posts(self, alice_client, alice, alice_post):
        resp = alice_client.get(BASE + f"{alice.username}/posts/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        ids = [p["id"] for p in data["results"]]
        assert alice_post.id in ids

    def test_paginated_response(self, alice_client, alice):
        for i in range(25):
            alice_client.post(
                "/api/v1/posts/create/",
                {"content": f"Post {i}", "visibility": "public"},
            )
        resp = alice_client.get(
            BASE + f"{alice.username}/posts/", {"page": 1}
        )
        data = resp.data["data"]
        assert len(data["results"]) == 20
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] >= 25

    def test_anonymous_can_view_public_posts(self, client, alice, alice_post):
        resp = client.get(BASE + f"{alice.username}/posts/")
        assert resp.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in resp.data["data"]["results"]]
        assert alice_post.id in ids


class TestGuestbookCreate:
    """POST /profiles/{username_or_id}/guestbook/create/ — PRD §2.5.4"""

    def test_create_entry_on_other_profile(self, alice_client, alice, bob):
        resp = alice_client.post(
            BASE + f"{bob.username}/guestbook/create/", {"content": "Hi Bob!"}
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["content"] == "Hi Bob!"

    def test_guestbook_entry_has_expected_fields(self, alice_client, alice, bob):
        resp = alice_client.post(
            BASE + f"{bob.username}/guestbook/create/", {"content": "Hello"}
        )
        entry = resp.data["data"]
        expected = {"id", "user", "content", "reply", "replied_at", "created_at"}
        assert expected - set(entry.keys()) == set()
        assert entry["user"]["user_id"] == alice.id

    def test_create_entry_requires_auth(self, client, bob):
        resp = client.post(
            BASE + f"{bob.username}/guestbook/create/", {"content": "Hack"}
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_create_entry_empty_content_rejected(self, alice_client, bob):
        resp = alice_client.post(
            BASE + f"{bob.username}/guestbook/create/", {"content": ""}
        )
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class TestGuestbookReply:
    """POST /profiles/guestbook/{entry_id}/reply/ — PRD §2.5.4"""

    def test_profile_owner_can_reply(self, alice_client, bob, alice_profile):
        entry = GuestbookEntry.objects.create(
            profile=alice_profile, author=bob, content="Nice page!",
        )
        resp = alice_client.post(
            BASE + f"guestbook/{entry.id}/reply/", {"reply": "Thanks!"}
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_non_owner_cannot_reply(self, charlie_client, alice, alice_profile):
        entry = GuestbookEntry.objects.create(
            profile=alice_profile, author=alice, content="Hi",
        )
        resp = charlie_client.post(
            BASE + f"guestbook/{entry.id}/reply/", {"reply": "Reply"}
        )
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_reply_requires_auth(self, client, bob, alice_profile):
        entry = GuestbookEntry.objects.create(
            profile=alice_profile, author=bob, content="Test"
        )
        resp = client.post(
            BASE + f"guestbook/{entry.id}/reply/", {"reply": "Hack"}
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestGuestbookDelete:
    """DELETE /profiles/guestbook/{entry_id}/delete/ — PRD §2.5.4"""

    def test_profile_owner_can_delete(self, alice_client, bob, alice_profile):
        entry = GuestbookEntry.objects.create(
            profile=alice_profile, author=bob, content="Delete me",
        )
        resp = alice_client.delete(BASE + f"guestbook/{entry.id}/delete/")
        assert resp.status_code == status.HTTP_200_OK

    def test_non_owner_cannot_delete(self, charlie_client, alice, alice_profile):
        entry = GuestbookEntry.objects.create(
            profile=alice_profile, author=alice, content="Keep me",
        )
        resp = charlie_client.delete(BASE + f"guestbook/{entry.id}/delete/")
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_nonexistent_entry(self, alice_client):
        resp = alice_client.delete(BASE + "guestbook/99999/delete/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_requires_auth(self, client, bob, alice_profile):
        entry = GuestbookEntry.objects.create(
            profile=alice_profile, author=bob, content="Test",
        )
        resp = client.delete(BASE + f"guestbook/{entry.id}/delete/")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestGuestbookList:
    """GET /profiles/{username_or_id}/guestbook/ — PRD §2.5.4"""

    def test_list_guestbook_entries(self, alice_client, alice, bob, bob_profile):
        GuestbookEntry.objects.create(
            profile=bob_profile, author=alice, content="Hello Bob",
        )
        resp = alice_client.get(BASE + f"{bob.username}/guestbook/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert len(data["results"]) >= 1
        assert data["results"][0]["content"] == "Hello Bob"

    def test_guestbook_list_is_paginated(self, alice_client, alice, bob, bob_profile):
        for i in range(25):
            GuestbookEntry.objects.create(
                profile=bob_profile, author=alice,
                content=f"Entry {i}",
            )
        resp = alice_client.get(
            BASE + f"{bob.username}/guestbook/", {"page": 1}
        )
        data = resp.data["data"]
        assert data["page_size"] == 20


class TestVisitors:
    """GET /profiles/{username_or_id}/visitors/ — PRD §2.1.4"""

    def test_own_visitor_list(self, alice_client, bob, alice):
        VisitRecord.objects.create(visitor=bob, visited_user=alice)
        resp = alice_client.get(BASE + f"{alice.username}/visitors/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        user_ids = [v["user_id"] for v in data["results"]]
        assert bob.id in user_ids

    def test_visitor_list_pagination(self, alice_client, alice):
        for i in range(25):
            u = User.objects.create_user(
                username=f"visitor{i}", password="Pass1234!"
            )
            VisitRecord.objects.create(visitor=u, visited_user=alice)

        resp = alice_client.get(
            BASE + f"{alice.username}/visitors/", {"page": 1, "page_size": 20}
        )
        data = resp.data["data"]
        assert len(data["results"]) == 20
        assert data["total"] >= 25

    def test_visitor_public_false_non_owner_gets_403(
        self, bob_client, alice
    ):
        profile = UserProfile.objects.get(user=alice)
        profile.visitor_public = False
        profile.save()
        resp = bob_client.get(BASE + f"{alice.username}/visitors/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_visitor_list_requires_auth(self, client, alice):
        resp = client.get(BASE + f"{alice.username}/visitors/")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
