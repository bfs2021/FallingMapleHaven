import io
import tempfile
from unittest.mock import PropertyMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _test_media_root(settings):
    """测试文件写入临时目录，不污染 media/ 文件夹"""
    tmp = tempfile.mkdtemp()
    settings.MEDIA_ROOT = tmp


@pytest.fixture(autouse=True)
def _no_anon_throttle():
    """全局关闭匿名限流：所有测试请求都来自 127.0.0.1，共享 10/min 滑窗配额，
    大量匿名请求会按真实耗时随机吃到 429，造成顺序依赖的偶发失败；没有测试依赖限流行为。
    注意必须直接改限流类的费率表：SimpleRateThrottle.THROTTLE_RATES 在 DRF 导入时就绑定了
    settings 里的字典，之后覆盖 REST_FRAMEWORK 或清理 api_settings 缓存都影响不到该引用。"""
    from rest_framework.throttling import (
        AnonRateThrottle,
        ScopedRateThrottle,
        SimpleRateThrottle,
        UserRateThrottle,
    )

    throttle_classes = (SimpleRateThrottle, AnonRateThrottle, UserRateThrottle, ScopedRateThrottle)
    snapshots = []
    for throttle_cls in throttle_classes:
        rates = getattr(throttle_cls, "THROTTLE_RATES", None)
        if isinstance(rates, dict):
            snapshots.append((rates, dict(rates)))
            rates["anon"] = None
    try:
        yield
    finally:
        for rates, snapshot in snapshots:
            rates.clear()
            rates.update(snapshot)

from apps.chat.models import ChatRoom, ChatRoomMember, Message
from apps.feed.models import Post
from apps.friends.models import Friendship
from apps.groups.models import GroupMember, InterestGroup
from apps.notifications.models import Notification
from apps.plugins.models import Plugin
from apps.profiles.models import GuestbookEntry, UserProfile, VisitRecord

User = get_user_model()


# ── User Fixtures ─────────────────────────────────────────────

@pytest.fixture
def alice(db):
    return User.objects.create_user(
        username="alice", password="Pass1234!", nickname="Alice"
    )


@pytest.fixture
def bob(db):
    return User.objects.create_user(
        username="bob", password="Pass1234!", nickname="Bob"
    )


@pytest.fixture
def charlie(db):
    return User.objects.create_user(
        username="charlie", password="Pass1234!", nickname="Charlie"
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staff", password="Pass1234!", nickname="Staff", is_staff=True
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin", password="Pass1234!", nickname="Admin",
        is_staff=True, is_superuser=True,
    )


# ── Client Fixtures ───────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def alice_client(alice):
    c = APIClient()
    c.force_authenticate(user=alice)
    return c


@pytest.fixture
def bob_client(bob):
    c = APIClient()
    c.force_authenticate(user=bob)
    return c


@pytest.fixture
def charlie_client(charlie):
    c = APIClient()
    c.force_authenticate(user=charlie)
    return c


@pytest.fixture
def staff_client(staff_user):
    c = APIClient()
    c.force_authenticate(user=staff_user)
    return c


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


# ── Profile Fixtures ──────────────────────────────────────────

@pytest.fixture
def alice_profile(alice):
    profile, _ = UserProfile.objects.get_or_create(user=alice)
    return profile


@pytest.fixture
def bob_profile(bob):
    profile, _ = UserProfile.objects.get_or_create(user=bob)
    return profile


# ── Feed Fixtures ─────────────────────────────────────────────

@pytest.fixture
def alice_post(alice):
    return Post.objects.create(author=alice, content="Hello from Alice")


@pytest.fixture
def bob_post(bob):
    return Post.objects.create(author=bob, content="Hello from Bob")


@pytest.fixture
def public_post(alice):
    return Post.objects.create(author=alice, content="Public post", visibility="public")


@pytest.fixture
def friends_post(alice):
    return Post.objects.create(author=alice, content="Friends only", visibility="friends")


# ── Friend Fixtures ───────────────────────────────────────────

@pytest.fixture
def friendship(alice, bob):
    return Friendship.objects.create(from_user=alice, to_user=bob, status="accepted")


@pytest.fixture
def pending_friend_request(alice, bob):
    return Friendship.objects.create(from_user=bob, to_user=alice, status="pending")


# ── Chat Fixtures ─────────────────────────────────────────────

@pytest.fixture
def private_room(alice, bob):
    room = ChatRoom.objects.create(room_type="private")
    ChatRoomMember.objects.create(room=room, user=alice)
    ChatRoomMember.objects.create(room=room, user=bob)
    return room


@pytest.fixture
def group_room(alice, bob, test_group):
    room = ChatRoom.objects.create(
        name=test_group.name, room_type=ChatRoom.Type.GROUP, group=test_group
    )
    ChatRoomMember.objects.create(room=room, user=alice)
    ChatRoomMember.objects.create(room=room, user=bob)
    return room


# ── Group Fixtures ────────────────────────────────────────────

@pytest.fixture
def test_group(alice):
    group = InterestGroup.objects.create(name="Test Group", creator=alice, is_public=True)
    GroupMember.objects.create(group=group, user=alice, role="admin")
    return group


@pytest.fixture
def private_group(alice):
    group = InterestGroup.objects.create(name="Private Group", creator=alice, is_public=False)
    GroupMember.objects.create(group=group, user=alice, role="admin")
    return group


@pytest.fixture
def group_member(test_group, bob):
    return GroupMember.objects.create(group=test_group, user=bob, role="member")


# ── Notification Fixtures ─────────────────────────────────────

@pytest.fixture
def notification(alice, bob):
    return Notification.objects.create(
        recipient=alice,
        sender=bob,
        notification_type="friend_request",
        title="好友请求",
        content="Bob 请求添加你为好友",
    )


# ── Helper: fake image file ───────────────────────────────────

@pytest.fixture
def fake_image():
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")
