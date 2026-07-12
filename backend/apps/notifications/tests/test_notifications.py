import pytest
from django.contrib.auth import get_user_model
from apps.feed.models import Comment, Like
from apps.friends.models import Friendship
from apps.notifications.models import Notification

User = get_user_model()

pytestmark = pytest.mark.django_db

# ── Helpers ────────────────────────────────────────────────────────────────

NOTIFICATION_LIST_URL = "/api/v1/notifications/"
NOTIFICATION_READ_ALL_URL = "/api/v1/notifications/read-all/"
NOTIFICATION_UNREAD_COUNT_URL = "/api/v1/notifications/unread-count/"


def notification_read_url(pk):
    return f"/api/v1/notifications/{pk}/read/"


def assert_api_success(response, expected_data_key=None):
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    if expected_data_key is not None:
        assert expected_data_key in body["data"]
    return body


def assert_api_error(response, status_code, code):
    assert response.status_code == status_code
    body = response.json()
    assert body["code"] == code
    return body


# ── NotificationListView ──────────────────────────────────────────────────


class TestNotificationListView:
    def test_returns_paginated_notifications(self, alice_client, notification):
        Notification.objects.create(
            recipient=notification.recipient,
            sender=notification.sender,
            notification_type="like",
            title="点赞",
        )
        resp = alice_client.get(NOTIFICATION_LIST_URL)
        body = assert_api_success(resp, "results")
        data = body["data"]
        assert data["total"] >= 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["results"]) >= 2

    def test_does_not_return_other_users_notifications(self, alice_client, bob_client, notification):
        resp = bob_client.get(NOTIFICATION_LIST_URL)
        body = assert_api_success(resp, "results")
        assert body["data"]["total"] == 0
        assert body["data"]["results"] == []

    def test_unread_only_filter(self, alice_client, notification):
        Notification.objects.filter(pk=notification.pk).update(is_read=True)
        Notification.objects.create(
            recipient=notification.recipient,
            sender=notification.sender,
            notification_type="like",
            title="未读点赞",
        )
        resp = alice_client.get(f"{NOTIFICATION_LIST_URL}?unread_only=true")
        body = assert_api_success(resp, "results")
        assert body["data"]["total"] == 1
        for n in body["data"]["results"]:
            assert n["is_read"] is False

    def test_unread_only_false_shows_all(self, alice_client, notification):
        Notification.objects.filter(pk=notification.pk).update(is_read=True)
        resp = alice_client.get(f"{NOTIFICATION_LIST_URL}?unread_only=false")
        body = assert_api_success(resp, "results")
        assert body["data"]["total"] == 1

    def test_unread_only_1_also_filters(self, alice_client, notification):
        Notification.objects.filter(pk=notification.pk).update(is_read=True)
        Notification.objects.create(
            recipient=notification.recipient,
            sender=notification.sender,
            notification_type="like",
            title="未读点赞",
        )
        resp = alice_client.get(f"{NOTIFICATION_LIST_URL}?unread_only=1")
        body = assert_api_success(resp, "results")
        assert body["data"]["total"] == 1

    def test_empty_when_no_notifications(self, bob_client):
        resp = bob_client.get(NOTIFICATION_LIST_URL)
        body = assert_api_success(resp, "results")
        assert body["data"]["total"] == 0
        assert body["data"]["results"] == []

    def test_returns_403_when_not_authenticated(self, client):
        resp = client.get(NOTIFICATION_LIST_URL)
        assert resp.status_code == 403

    def test_serializer_fields(self, alice_client, notification):
        resp = alice_client.get(NOTIFICATION_LIST_URL)
        body = assert_api_success(resp, "results")
        result = body["data"]["results"][0]
        expected_keys = {"id", "notification_type", "title", "content", "link", "is_read", "created_at"}
        assert set(result.keys()) == expected_keys

    def test_pagination_page_2(self, alice_client):
        for i in range(25):
            Notification.objects.create(
                recipient=alice_client.handler._force_user,
                sender=None,
                notification_type="system",
                title=f"通知{i}",
            )
        resp = alice_client.get(f"{NOTIFICATION_LIST_URL}?page=2")
        body = assert_api_success(resp, "results")
        assert body["data"]["page"] == 2
        assert body["data"]["total"] == 25
        assert len(body["data"]["results"]) == 5


# ── NotificationReadView ──────────────────────────────────────────────────


class TestNotificationReadView:
    def test_mark_single_as_read(self, alice_client, notification):
        assert Notification.objects.get(pk=notification.pk).is_read is False
        resp = alice_client.post(notification_read_url(notification.pk))
        assert_api_success(resp)
        assert Notification.objects.get(pk=notification.pk).is_read is True

    def test_cannot_mark_another_users_notification(self, bob_client, notification):
        resp = bob_client.post(notification_read_url(notification.pk))
        assert_api_error(resp, 404, 40004)

    def test_non_existent_notification_404(self, alice_client):
        resp = alice_client.post(notification_read_url(99999))
        assert_api_error(resp, 404, 40004)

    def test_already_read_is_idempotent(self, alice_client, notification):
        Notification.objects.filter(pk=notification.pk).update(is_read=True)
        resp = alice_client.post(notification_read_url(notification.pk))
        assert_api_success(resp)
        assert Notification.objects.get(pk=notification.pk).is_read is True

    def test_returns_403_when_not_authenticated(self, client, notification):
        resp = client.post(notification_read_url(notification.pk))
        assert resp.status_code == 403


# ── NotificationReadAllView ───────────────────────────────────────────────


class TestNotificationReadAllView:
    def test_mark_all_as_read(self, alice_client, alice, bob):
        n1 = Notification.objects.create(recipient=alice, sender=bob, notification_type="like", title="点赞1")
        n2 = Notification.objects.create(recipient=alice, sender=bob, notification_type="comment", title="评论1")
        resp = alice_client.post(NOTIFICATION_READ_ALL_URL)
        assert_api_success(resp)
        assert Notification.objects.get(pk=n1.pk).is_read is True
        assert Notification.objects.get(pk=n2.pk).is_read is True

    def test_does_not_affect_other_users(self, alice_client, bob_client, alice, bob):
        bob_n = Notification.objects.create(recipient=bob, sender=alice, notification_type="like", title="bob的通知")
        alice_client.post(NOTIFICATION_READ_ALL_URL)
        assert Notification.objects.get(pk=bob_n.pk).is_read is False

    def test_empty_read_all_is_ok(self, bob_client):
        resp = bob_client.post(NOTIFICATION_READ_ALL_URL)
        assert_api_success(resp)

    def test_returns_403_when_not_authenticated(self, client):
        resp = client.post(NOTIFICATION_READ_ALL_URL)
        assert resp.status_code == 403


# ── UnreadCountView ───────────────────────────────────────────────────────


class TestUnreadCountView:
    def test_returns_correct_unread_count(self, alice_client, alice, bob):
        Notification.objects.create(recipient=alice, sender=bob, notification_type="like", title="点赞")
        Notification.objects.create(recipient=alice, sender=bob, notification_type="comment", title="评论")
        Notification.objects.create(recipient=alice, sender=bob, is_read=True, notification_type="system", title="已读")
        resp = alice_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        body = assert_api_success(resp, "count")
        assert body["data"]["count"] == 2

    def test_after_reading_one_count_decreases(self, alice_client, alice, bob):
        n1 = Notification.objects.create(recipient=alice, sender=bob, notification_type="like", title="点赞")
        Notification.objects.create(recipient=alice, sender=bob, notification_type="comment", title="评论")
        alice_client.post(notification_read_url(n1.pk))
        resp = alice_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        body = assert_api_success(resp, "count")
        assert body["data"]["count"] == 1

    def test_after_read_all_count_is_zero(self, alice_client, alice, bob):
        Notification.objects.create(recipient=alice, sender=bob, notification_type="like", title="点赞")
        Notification.objects.create(recipient=alice, sender=bob, notification_type="comment", title="评论")
        alice_client.post(NOTIFICATION_READ_ALL_URL)
        resp = alice_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        body = assert_api_success(resp, "count")
        assert body["data"]["count"] == 0

    def test_zero_when_no_notifications(self, bob_client):
        resp = bob_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        body = assert_api_success(resp, "count")
        assert body["data"]["count"] == 0

    def test_returns_403_when_not_authenticated(self, client):
        resp = client.get(NOTIFICATION_UNREAD_COUNT_URL)
        assert resp.status_code == 403


# ── Signal: handle_friend_request ─────────────────────────────────────────


class TestFriendRequestSignal:
    def test_sending_friend_request_creates_notification(self, alice, bob):
        Friendship.objects.create(from_user=alice, to_user=bob, status="pending")
        notification = Notification.objects.filter(
            recipient=bob,
            sender=alice,
            notification_type="friend_request",
        ).first()
        assert notification is not None
        assert notification.title == "好友请求"

    def test_accepting_friend_request_creates_notification(self, alice, bob):
        friendship = Friendship.objects.create(from_user=alice, to_user=bob, status="pending")
        friendship.status = Friendship.Status.ACCEPTED
        friendship.save(update_fields=["status"])
        notification = Notification.objects.filter(
            recipient=alice,
            sender=bob,
            notification_type="friend_accepted",
        ).first()
        assert notification is not None
        assert notification.title == "好友请求已接受"

    def test_rejecting_does_not_create_notification(self, alice, bob):
        friendship = Friendship.objects.create(from_user=alice, to_user=bob, status="pending")
        notification_count = Notification.objects.count()
        friendship.status = Friendship.Status.REJECTED
        friendship.save(update_fields=["status"])
        assert Notification.objects.count() == notification_count

    def test_accepted_friendship_directly_creates_accepted_notification(self, alice, bob):
        Friendship.objects.create(from_user=alice, to_user=bob, status="accepted")
        friend_request_n = Notification.objects.filter(
            recipient=bob, sender=alice, notification_type="friend_request"
        )
        friend_accepted_n = Notification.objects.filter(
            recipient=alice, sender=bob, notification_type="friend_accepted"
        )
        assert not friend_request_n.exists()
        assert friend_accepted_n.exists()


# ── Signal: handle_like ───────────────────────────────────────────────────


class TestLikeSignal:
    def test_liking_post_creates_notification(self, alice, bob, alice_post):
        Like.objects.create(post=alice_post, user=bob)
        notification = Notification.objects.filter(
            recipient=alice,
            sender=bob,
            notification_type="like",
        ).first()
        assert notification is not None
        assert notification.title == "收到点赞"
        assert "Bob" in notification.content

    def test_liking_own_post_does_not_create_notification(self, alice, alice_post):
        Like.objects.create(post=alice_post, user=alice)
        assert Notification.objects.count() == 0

    def test_liking_same_post_twice_only_creates_one_notification(self, alice, bob, alice_post):
        Like.objects.create(post=alice_post, user=bob)
        Notification.objects.all().delete()
        like, created = Like.objects.get_or_create(post=alice_post, user=bob)
        assert created is False
        assert Notification.objects.count() == 0

    def test_liking_other_users_post(self, alice, bob, charlie, alice_post):
        Like.objects.create(post=alice_post, user=bob)
        Like.objects.create(post=alice_post, user=charlie)
        notifications = Notification.objects.filter(
            recipient=alice, notification_type="like"
        )
        assert notifications.count() == 2


# ── Signal: handle_comment ────────────────────────────────────────────────


class TestCommentSignal:
    def test_comment_on_post_creates_notification_for_author(self, alice, bob, alice_post):
        Comment.objects.create(post=alice_post, author=bob, content="Great post!")
        notification = Notification.objects.filter(
            recipient=alice,
            sender=bob,
            notification_type="comment",
        ).first()
        assert notification is not None
        assert notification.title == "收到评论"
        assert "Great post!" in notification.content

    def test_comment_on_own_post_does_not_create_notification(self, alice, alice_post):
        Comment.objects.create(post=alice_post, author=alice, content="My own comment")
        assert Notification.objects.count() == 0

    def test_reply_to_comment_creates_notification_for_comment_author(self, alice, bob, charlie, alice_post):
        parent = Comment.objects.create(post=alice_post, author=alice, content="Original")
        Comment.objects.create(post=alice_post, author=bob, content="Reply!", parent=parent)
        notification = Notification.objects.filter(
            recipient=alice,
            sender=bob,
            notification_type="reply",
        ).first()
        assert notification is not None
        assert notification.title == "收到回复"
        assert "Reply!" in notification.content

    def test_reply_to_own_comment_does_not_create_notification(self, alice, alice_post):
        parent = Comment.objects.create(post=alice_post, author=alice, content="Original")
        Comment.objects.create(post=alice_post, author=alice, content="Self reply", parent=parent)
        comment_notifications = Notification.objects.filter(notification_type="comment")
        reply_notifications = Notification.objects.filter(notification_type="reply")
        assert comment_notifications.count() == 0
        assert reply_notifications.count() == 0

    def test_comment_also_creates_reply_when_reply_to_others(self, alice, bob, charlie, alice_post):
        parent = Comment.objects.create(post=alice_post, author=bob, content="Bob's comment")
        Comment.objects.create(post=alice_post, author=charlie, content="Charlie reply", parent=parent)
        comment_n = Notification.objects.filter(
            recipient=alice, sender=charlie, notification_type="comment"
        )
        reply_n = Notification.objects.filter(
            recipient=bob, sender=charlie, notification_type="reply"
        )
        assert comment_n.exists()
        assert reply_n.exists()

    def test_reply_on_own_post_creates_reply_notification(self, alice, bob, alice_post):
        parent = Comment.objects.create(post=alice_post, author=bob, content="Bob's comment")
        Comment.objects.create(post=alice_post, author=alice, content="Alice reply", parent=parent)
        comment_n = Notification.objects.filter(notification_type="comment", sender=alice)
        reply_n = Notification.objects.filter(
            recipient=bob, sender=alice, notification_type="reply"
        )
        assert comment_n.count() == 0
        assert reply_n.exists()

    def test_editing_comment_does_not_create_new_notification(self, alice, bob, alice_post):
        comment = Comment.objects.create(post=alice_post, author=bob, content="Original")
        Notification.objects.all().delete()
        comment.content = "Edited"
        comment.save(update_fields=["content"])
        assert Notification.objects.count() == 0
