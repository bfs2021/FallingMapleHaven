import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.feed.models import Post
from apps.profiles.models import GuestbookEntry, VisitRecord

User = get_user_model()

PROFILES_URL = "/api/v1/profiles/"


@pytest.mark.django_db
class TestProfileView:
    def test_own_profile(self, alice_client, alice, alice_profile):
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["user_id"] == alice.id
        assert data["nickname"] == alice.nickname
        assert data["friend_status"] == "self"
        assert "is_owner" not in data  # not in actual serializer

    def test_friend_profile(self, alice_client, bob, alice_profile, bob_profile, friendship):
        response = alice_client.get(f"{PROFILES_URL}{bob.username}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["user_id"] == bob.id
        assert data["friend_status"] == "accepted"

    def test_stranger_profile(self, charlie_client, alice, alice_profile):
        response = charlie_client.get(f"{PROFILES_URL}{alice.username}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["user_id"] == alice.id
        assert data["friend_status"] == "none"

    def test_non_existent_user_404(self, alice_client):
        response = alice_client.get(f"{PROFILES_URL}nonexistent/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["code"] == 40004

    def test_unauthenticated_user(self, client, alice, alice_profile):
        response = client.get(f"{PROFILES_URL}{alice.username}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["user_id"] == alice.id
        assert data["friend_status"] == "none"

    def test_lookup_by_id(self, alice_client, alice, alice_profile):
        response = alice_client.get(f"{PROFILES_URL}{alice.id}/", {"lookup": "id"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["user_id"] == alice.id

    def test_visit_record_created_on_other_profile_view(self, alice, alice_client, bob, bob_profile):
        assert VisitRecord.objects.filter(visitor=alice, visited_user=bob).count() == 0
        alice_client.get(f"{PROFILES_URL}{bob.username}/")
        assert VisitRecord.objects.filter(visitor=alice, visited_user=bob).count() == 1

    def test_visit_record_not_created_on_own_profile(self, alice_client, alice, alice_profile):
        assert VisitRecord.objects.filter(visitor=alice, visited_user=alice).count() == 0
        alice_client.get(f"{PROFILES_URL}{alice.username}/")
        assert VisitRecord.objects.filter(visitor=alice, visited_user=alice).count() == 0

    def test_visit_record_updated_on_revisit(self, alice, alice_client, bob, bob_profile):
        VisitRecord.objects.create(visitor=alice, visited_user=bob)
        alice_client.get(f"{PROFILES_URL}{bob.username}/")
        assert VisitRecord.objects.filter(visitor=alice, visited_user=bob).count() == 1


@pytest.mark.django_db
class TestVisitorListView:
    def test_own_visitors(self, alice_client, alice, bob, charlie):
        VisitRecord.objects.create(visitor=bob, visited_user=alice)
        VisitRecord.objects.create(visitor=charlie, visited_user=alice)
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/visitors/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 2
        assert len(response.data["data"]["results"]) == 2

    def test_empty_visitors(self, alice_client, alice):
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/visitors/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 0
        assert response.data["data"]["results"] == []

    def test_unauthorized_403(self, client, alice):
        response = client.get(f"{PROFILES_URL}{alice.username}/visitors/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_visitor_public_false_stranger_403(self, alice, alice_client, bob, bob_profile, charlie_client):
        bob_profile.visitor_public = False
        bob_profile.save()
        VisitRecord.objects.create(visitor=alice, visited_user=bob)
        response = charlie_client.get(f"{PROFILES_URL}{bob.username}/visitors/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == 40003

    def test_visitor_public_true_stranger_allowed(self, alice, alice_client, bob, bob_profile, charlie_client):
        VisitRecord.objects.create(visitor=alice, visited_user=bob)
        response = charlie_client.get(f"{PROFILES_URL}{bob.username}/visitors/")
        assert response.status_code == status.HTTP_200_OK

    def test_non_existent_user_404(self, alice_client):
        response = alice_client.get(f"{PROFILES_URL}nonexistent/visitors/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_pagination(self, alice_client, alice):
        for i in range(25):
            u = User.objects.create_user(username=f"visitor{i}", password="pass")
            VisitRecord.objects.create(visitor=u, visited_user=alice)
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/visitors/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 25
        assert len(response.data["data"]["results"]) == 20
        assert response.data["data"]["page"] == 1

    def test_second_page(self, alice_client, alice):
        for i in range(25):
            u = User.objects.create_user(username=f"visitor{i}", password="pass")
            VisitRecord.objects.create(visitor=u, visited_user=alice)
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/visitors/", {"page": 2})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["results"]) == 5


@pytest.mark.django_db
class TestUserPostListView:
    def test_own_posts_see_all(self, alice_client, alice, alice_post, public_post, friends_post):
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/posts/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 3

    def test_friend_sees_public_and_friends_posts(
        self, bob_client, alice, alice_post, public_post, friends_post, friendship
    ):
        response = bob_client.get(f"{PROFILES_URL}{alice.username}/posts/")
        assert response.status_code == status.HTTP_200_OK
        content_titles = {p["content"] for p in response.data["data"]["results"]}
        assert "Public post" in content_titles
        assert "Friends only" in content_titles

    def test_friend_does_not_see_private_posts(
        self, bob_client, alice, public_post, friends_post, friendship
    ):
        private = Post.objects.create(author=alice, content="Private post", visibility=Post.Visibility.PRIVATE)
        response = bob_client.get(f"{PROFILES_URL}{alice.username}/posts/")
        assert response.status_code == status.HTTP_200_OK
        content_titles = {p["content"] for p in response.data["data"]["results"]}
        assert "Private post" not in content_titles

    def test_stranger_only_sees_public_posts(
        self, charlie_client, alice, public_post, friends_post
    ):
        response = charlie_client.get(f"{PROFILES_URL}{alice.username}/posts/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 1
        assert response.data["data"]["results"][0]["content"] == "Public post"

    def test_unauthenticated_only_sees_public_posts(
        self, client, alice, public_post, friends_post
    ):
        response = client.get(f"{PROFILES_URL}{alice.username}/posts/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 1
        assert response.data["data"]["results"][0]["content"] == "Public post"

    def test_no_posts_empty(self, alice_client, bob):
        response = alice_client.get(f"{PROFILES_URL}{bob.username}/posts/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 0
        assert response.data["data"]["results"] == []

    def test_non_existent_user_404(self, alice_client):
        response = alice_client.get(f"{PROFILES_URL}nonexistent/posts/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_pagination(self, alice_client, alice):
        for i in range(25):
            Post.objects.create(author=alice, content=f"Post {i}", visibility=Post.Visibility.PUBLIC)
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/posts/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 25
        assert len(response.data["data"]["results"]) == 20


@pytest.mark.django_db
class TestGuestbookListView:
    def test_empty_guestbook(self, alice_client, alice, alice_profile):
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/guestbook/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 0
        assert response.data["data"]["results"] == []

    def test_with_entries(self, alice_client, alice, alice_profile, bob):
        GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hello!")
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/guestbook/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 1
        assert response.data["data"]["results"][0]["content"] == "Hello!"

    def test_multiple_entries_pagination(self, alice_client, alice, alice_profile, bob):
        for i in range(25):
            GuestbookEntry.objects.create(profile=alice_profile, author=bob, content=f"Entry {i}")
        response = alice_client.get(f"{PROFILES_URL}{alice.username}/guestbook/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 25
        assert len(response.data["data"]["results"]) == 20

    def test_unauthenticated_access_allowed(self, client, alice, alice_profile, bob):
        GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hello!")
        response = client.get(f"{PROFILES_URL}{alice.username}/guestbook/")
        assert response.status_code == status.HTTP_200_OK

    def test_non_existent_user_404(self, alice_client):
        response = alice_client.get(f"{PROFILES_URL}nonexistent/guestbook/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestGuestbookCreateView:
    def test_create_entry(self, alice_client, bob, bob_profile):
        response = alice_client.post(
            f"{PROFILES_URL}{bob.username}/guestbook/create/",
            {"content": "Nice profile!"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["content"] == "Nice profile!"
        assert GuestbookEntry.objects.count() == 1

    def test_missing_content_error(self, alice_client, bob, bob_profile):
        response = alice_client.post(
            f"{PROFILES_URL}{bob.username}/guestbook/create/",
            {},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthorized_403(self, client, bob, bob_profile):
        response = client.post(
            f"{PROFILES_URL}{bob.username}/guestbook/create/",
            {"content": "Hello"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_existent_user_404(self, alice_client):
        response = alice_client.post(
            f"{PROFILES_URL}nonexistent/guestbook/create/",
            {"content": "Hello"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestGuestbookReplyView:
    def test_owner_can_reply(self, alice_client, alice, alice_profile, bob):
        entry = GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hi")
        response = alice_client.post(
            f"{PROFILES_URL}guestbook/{entry.id}/reply/",
            {"reply": "Thanks!"},
        )
        assert response.status_code == status.HTTP_200_OK
        entry.refresh_from_db()
        assert entry.reply == "Thanks!"
        assert entry.replied_at is not None

    def test_non_owner_cannot_reply(self, bob_client, alice, alice_profile):
        entry = GuestbookEntry.objects.create(profile=alice_profile, author=alice, content="Hi")
        response = bob_client.post(
            f"{PROFILES_URL}guestbook/{entry.id}/reply/",
            {"reply": "Hacked!"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == 40003

    def test_non_existent_entry_404(self, alice_client):
        response = alice_client.post(
            f"{PROFILES_URL}guestbook/99999/reply/",
            {"reply": "Hello"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_missing_reply_field(self, alice_client, alice, alice_profile, bob):
        entry = GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hi")
        response = alice_client.post(
            f"{PROFILES_URL}guestbook/{entry.id}/reply/",
            {},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthorized_403(self, client, alice, alice_profile, bob):
        entry = GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hi")
        response = client.post(
            f"{PROFILES_URL}guestbook/{entry.id}/reply/",
            {"reply": "Thanks!"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestGuestbookDeleteView:
    def test_owner_can_delete(self, alice_client, alice, alice_profile, bob):
        entry = GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hi")
        response = alice_client.delete(f"{PROFILES_URL}guestbook/{entry.id}/delete/")
        assert response.status_code == status.HTTP_200_OK
        assert GuestbookEntry.objects.count() == 0

    def test_entry_author_cannot_delete(self, bob, bob_client, alice, alice_profile):
        entry = GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hi")
        response = bob_client.delete(f"{PROFILES_URL}guestbook/{entry.id}/delete/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == 40003

    def test_other_cannot_delete(self, charlie_client, alice, alice_profile, bob):
        entry = GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hi")
        response = charlie_client.delete(f"{PROFILES_URL}guestbook/{entry.id}/delete/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == 40003

    def test_non_existent_entry_404(self, alice_client):
        response = alice_client.delete(f"{PROFILES_URL}guestbook/99999/delete/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized_403(self, client, alice, alice_profile, bob):
        entry = GuestbookEntry.objects.create(profile=alice_profile, author=bob, content="Hi")
        response = client.delete(f"{PROFILES_URL}guestbook/{entry.id}/delete/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestProfileAdminView:
    def test_get_as_staff(self, staff_client, alice):
        response = staff_client.get(f"{PROFILES_URL}{alice.username}/admin/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["user_id"] == alice.id
        assert data["username"] == alice.username
        assert data["nickname"] == alice.nickname

    def test_get_as_normal_user_403(self, alice_client, bob):
        response = alice_client.get(f"{PROFILES_URL}{bob.username}/admin/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == 40003

    def test_get_non_existent_user_404(self, staff_client):
        response = staff_client.get(f"{PROFILES_URL}nonexistent/admin/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_as_staff(self, staff_client, alice):
        response = staff_client.patch(
            f"{PROFILES_URL}{alice.username}/admin/",
            {"is_active": False},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        alice.refresh_from_db()
        assert alice.is_active is False
        assert response.data["data"]["is_active"] == False

    def test_patch_as_normal_user_403(self, alice_client, bob):
        response = alice_client.patch(
            f"{PROFILES_URL}{bob.username}/admin/",
            {"is_active": False},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_non_existent_user_404(self, staff_client):
        response = staff_client.patch(
            f"{PROFILES_URL}nonexistent/admin/",
            {"is_active": False},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_allowed_fields_only_is_active(self, staff_client, alice):
        response = staff_client.patch(
            f"{PROFILES_URL}{alice.username}/admin/",
            {"is_active": False, "bio": "should be ignored"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        alice.refresh_from_db()
        assert alice.is_active is False
        assert alice.bio != "should be ignored"


# ── ⛓️ 路径解析契约 ─────────────────────────────────────────


class TestUsernameOrIdResolution:
    """C12/C13 回归：确保用户名（非 int ID）路径可以正确解析。"""

    def test_profile_by_username_string(self, client, alice):
        resp = client.get(f"{PROFILES_URL}{alice.username}/")
        assert resp.status_code == 200
        assert resp.data["data"]["user_id"] == alice.id

    def test_profile_by_numeric_username(self, client, db):
        """用户名为纯数字字符串时也应能解析。"""
        user = User.objects.create_user(
            username="12345", password="Pass1234!", nickname="Numbers"
        )
        resp = client.get(f"{PROFILES_URL}12345/")
        assert resp.status_code == 200
        assert resp.data["data"]["user_id"] == user.id

    def test_profile_by_id_integer(self, client, alice):
        resp = client.get(f"{PROFILES_URL}{alice.id}/")
        assert resp.status_code == 200
        assert resp.data["data"]["user_id"] == alice.id

    def test_admin_by_username_string(self, staff_client, alice):
        resp = staff_client.get(f"{PROFILES_URL}{alice.username}/admin/")
        assert resp.status_code == 200
        assert resp.data["data"]["user_id"] == alice.id

    def test_admin_by_numeric_username(self, staff_client, db):
        user = User.objects.create_user(
            username="999", password="Pass1234!", nickname="NumAdmin"
        )
        resp = staff_client.get(f"{PROFILES_URL}999/admin/")
        assert resp.status_code == 200
        assert resp.data["data"]["user_id"] == user.id

    def test_guestbook_by_username_string(self, client, alice, alice_profile):
        resp = client.get(f"{PROFILES_URL}{alice.username}/guestbook/")
        assert resp.status_code == 200

    def test_visitors_by_username_string(self, alice_client, bob, alice):
        VisitRecord.objects.create(visitor=bob, visited_user=alice)
        resp = alice_client.get(f"{PROFILES_URL}{alice.username}/visitors/")
        assert resp.status_code == 200

    def test_posts_by_username_string(self, alice_client, alice, public_post):
        resp = alice_client.get(f"{PROFILES_URL}{alice.username}/posts/")
        assert resp.status_code == 200
