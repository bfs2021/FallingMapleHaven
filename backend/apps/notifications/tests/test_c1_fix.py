import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from apps.notifications.models import Notification
from apps.groups.models import InterestGroup, GroupMember
from apps.feed.models import Post

User = get_user_model()


@pytest.mark.django_db
class TestC1NotificationTypeField:
    def test_type_kwarg_raises_type_error(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        with pytest.raises(TypeError, match="type"):
            Notification.objects.create(
                recipient=alice,
                sender=bob,
                type="friend_request",
            )

    def test_notification_type_kwarg_succeeds(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        notification = Notification.objects.create(
            recipient=alice,
            sender=bob,
            notification_type="friend_request",
            title="Test",
            content="Hello",
        )
        assert notification.notification_type == "friend_request"
        assert notification.recipient == alice
        assert notification.sender == bob

    def test_group_join_request_notification(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        group = InterestGroup.objects.create(name="Test Group", creator=alice, is_public=True)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        notification = Notification.objects.create(
            recipient=alice,
            sender=bob,
            notification_type="group_join_request",
            title="加入小组申请",
            content="申请",
            link=f"/groups/{group.id}",
        )
        assert notification.notification_type == "group_join_request"

    def test_group_member_joined_notification(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        notification = Notification.objects.create(
            recipient=alice,
            sender=bob,
            notification_type="group_member_joined",
            title="新成员加入",
            content="欢迎",
        )
        assert notification.notification_type == "group_member_joined"

    def test_group_request_approved_notification(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        notification = Notification.objects.create(
            recipient=alice,
            sender=bob,
            notification_type="group_request_approved",
            title="申请已通过",
        )
        assert notification.notification_type == "group_request_approved"

    def test_group_request_rejected_notification(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        notification = Notification.objects.create(
            recipient=alice,
            sender=bob,
            notification_type="group_request_rejected",
            title="申请已拒绝",
        )
        assert notification.notification_type == "group_request_rejected"

    def test_bulk_create_with_notification_type(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        charlie = User.objects.create_user(username="charlie", password="pass")
        notifications = Notification.objects.bulk_create([
            Notification(
                recipient=m.user,
                sender=bob,
                notification_type="group_member_joined",
            )
            for m in [
                type("obj", (object,), {"user": alice})(),
                type("obj", (object,), {"user": charlie})(),
            ]
        ])
        assert len(notifications) == 2
        for n in notifications:
            assert n.notification_type == "group_member_joined"


