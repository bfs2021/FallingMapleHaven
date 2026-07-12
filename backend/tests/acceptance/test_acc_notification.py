import pytest
from rest_framework import status

from apps.friends.models import Friendship
from apps.notifications.models import Notification

BASE = "/api/v1/notifications/"

pytestmark = pytest.mark.django_db


class TestNotificationOnLike:
    """PRD §2.8 — 点赞触发通知"""

    def test_like_creates_notification_for_post_author(self, alice_client, bob_client, alice, bob, alice_post):
        resp = bob_client.post(f"/api/v1/posts/{alice_post.id}/like/")
        assert resp.status_code == status.HTTP_200_OK

        notif = Notification.objects.filter(recipient=alice, sender=bob, notification_type="like").first()
        assert notif is not None
        assert notif.is_read is False

    def test_like_does_not_notify_self(self, alice_client, alice, alice_post):
        resp = alice_client.post(f"/api/v1/posts/{alice_post.id}/like/")
        assert resp.status_code == status.HTTP_200_OK

        assert Notification.objects.filter(recipient=alice, notification_type="like").count() == 0


class TestNotificationOnComment:
    """PRD §2.8 — 评论触发通知"""

    def test_comment_creates_notification_for_post_author(self, alice_client, bob_client, alice, bob, alice_post):
        resp = bob_client.post(f"/api/v1/posts/{alice_post.id}/comments/create/", {"content": "Nice!"})
        assert resp.status_code == status.HTTP_201_CREATED

        notif = Notification.objects.filter(recipient=alice, sender=bob, notification_type="comment").first()
        assert notif is not None
        assert notif.is_read is False


class TestNotificationOnFriendRequest:
    """PRD §2.2 / §2.8 — 好友请求触发通知"""

    def test_friend_request_creates_notification(self, alice_client, bob, notification, alice):
        # notification fixture is a friend_request from bob to alice
        notif = Notification.objects.filter(recipient=alice, sender=bob, notification_type="friend_request").first()
        assert notif is not None

    def test_accept_friend_request_creates_notification(self, alice_client, bob_client, alice, bob):
        # bob sends request to alice
        bob_client.post("/api/v1/friends/request/", {"to_user_id": alice.id})

        # alice accepts
        req = Friendship.objects.get(from_user=bob, to_user=alice, status="pending")
        alice_client.post("/api/v1/friends/handle/", {"request_id": req.id, "action": "accept"})

        notif = Notification.objects.filter(recipient=bob, sender=alice, notification_type="friend_accepted").first()
        assert notif is not None


class TestNotificationList:
    """GET /notifications/ — PRD §2.8"""

    def test_list_is_paginated(self, alice_client, alice, bob, notification):
        for i in range(15):
            Notification.objects.create(
                recipient=alice, sender=bob,
                notification_type="system",
                title=f"Notification {i}", content=f"Content {i}",
            )
        resp = alice_client.get(BASE, {"page": 1})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", {})
        assert "results" in data
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["total"] >= 15

        # second page yields the remaining
        resp2 = alice_client.get(BASE, {"page": 2})
        data2 = resp2.data.get("data", {})
        assert len(data2["results"]) >= 0
        assert len(data["results"]) + len(data2["results"]) == data["total"]

    def test_list_contains_expected_fields(self, alice_client, alice, bob, notification):
        resp = alice_client.get(BASE)
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("data", {}).get("results", [])
        assert len(results) >= 1
        item = results[0]
        for field in ("id", "notification_type", "title", "content", "is_read", "created_at", "link"):
            assert field in item, f"Missing field: {field}"

    def test_list_mixed_types(self, alice_client, alice, bob):
        for ntype in ("like", "comment", "system", "friend_request"):
            Notification.objects.create(
                recipient=alice, sender=bob,
                notification_type=ntype,
                title=f"Test {ntype}",
            )
        resp = alice_client.get(BASE)
        results = resp.data.get("data", {}).get("results", [])
        types = {r["notification_type"] for r in results}
        for ntype in ("like", "comment", "system", "friend_request"):
            assert ntype in types

    def test_list_requires_auth(self, client):
        resp = client.get(BASE)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_list_only_returns_own_notifications(self, alice_client, bob_client, alice, bob, charlie, notification):
        # notification is for alice
        resp = bob_client.get(BASE)
        results = resp.data.get("data", {}).get("results", [])
        bob_ids = {n["id"] for n in results}

        # bob should not see alice's notification
        assert notification.id not in bob_ids


class TestMarkSingleRead:
    """POST /notifications/{id}/read/ — PRD §2.8"""

    def test_mark_single_as_read(self, alice_client, notification):
        assert notification.is_read is False
        resp = alice_client.post(BASE + f"{notification.id}/read/")
        assert resp.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_cannot_mark_other_notification_as_read(self, bob_client, notification):
        resp = bob_client.post(BASE + f"{notification.id}/read/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_nonexistent_notification(self, alice_client):
        resp = alice_client.post(BASE + "99999/read/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_requires_auth(self, client, notification):
        resp = client.post(BASE + f"{notification.id}/read/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestMarkAllRead:
    """POST /notifications/read-all/ — PRD §2.8"""

    def test_mark_all_as_read(self, alice_client, alice, bob):
        for i in range(5):
            Notification.objects.create(
                recipient=alice, sender=bob,
                notification_type="system",
                title=f"Notif {i}",
            )
        resp = alice_client.post(BASE + "read-all/")
        assert resp.status_code == status.HTTP_200_OK
        unread = Notification.objects.filter(recipient=alice, is_read=False).count()
        assert unread == 0

    def test_read_all_only_affects_own(self, alice_client, bob_client, alice, bob, charlie):
        Notification.objects.create(recipient=alice, sender=charlie, notification_type="system", title="Alice's")
        Notification.objects.create(recipient=bob, sender=charlie, notification_type="system", title="Bob's")

        alice_client.post(BASE + "read-all/")

        assert Notification.objects.filter(recipient=alice, is_read=False).count() == 0
        assert Notification.objects.filter(recipient=bob, is_read=False).count() == 1

    def test_requires_auth(self, client):
        resp = client.post(BASE + "read-all/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestUnreadCount:
    """GET /notifications/unread-count/ — PRD §2.8"""

    def test_unread_count(self, alice_client, alice, bob, notification):
        resp = alice_client.get(BASE + "unread-count/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", {})
        assert "count" in data
        assert data["count"] >= 1

    def test_unread_count_zero(self, bob_client, bob):
        resp = bob_client.get(BASE + "unread-count/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data.get("data", {}).get("count") == 0

    def test_unread_count_updates_after_read(self, alice_client, alice, bob, notification):
        resp = alice_client.get(BASE + "unread-count/")
        count_before = resp.data.get("data", {}).get("count")

        alice_client.post(BASE + f"{notification.id}/read/")

        resp = alice_client.get(BASE + "unread-count/")
        count_after = resp.data.get("data", {}).get("count")
        assert count_after == count_before - 1

    def test_requires_auth(self, client):
        resp = client.get(BASE + "unread-count/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestNotificationAuth:
    """Auth-required endpoints all reject anonymous"""

    def test_all_endpoints_require_auth(self, client, alice, bob, notification):
        endpoints = [
            ("get", BASE, None),
            ("get", BASE + "unread-count/", None),
            ("post", BASE + f"{notification.id}/read/", None),
            ("post", BASE + "read-all/", None),
        ]
        for method, url, data in endpoints:
            if method == "get":
                resp = client.get(url, data or {})
            else:
                resp = client.post(url, data or {})
            assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN), f"{method.upper()} {url} returned {resp.status_code}"