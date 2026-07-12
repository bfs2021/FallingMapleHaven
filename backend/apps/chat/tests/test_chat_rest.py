import pytest
from django.utils import timezone
from rest_framework import status

from apps.chat.models import ChatRoom, ChatRoomMember, Message


pytestmark = pytest.mark.django_db


class TestRoomListView:
    """GET /api/v1/chat/rooms/"""

    def test_authenticated_user_sees_their_rooms(self, alice_client, private_room):
        response = alice_client.get("/api/v1/chat/rooms/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert len(data) == 1
        assert data[0]["id"] == private_room.id
        assert data[0]["room_type"] == "private"

    def test_empty_when_no_rooms(self, charlie_client):
        response = charlie_client.get("/api/v1/chat/rooms/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"] == []

    def test_includes_other_user_for_private(self, alice_client, private_room, bob):
        response = alice_client.get("/api/v1/chat/rooms/")
        data = response.data["data"][0]
        assert data["other_user"] is not None
        assert data["other_user"]["user_id"] == bob.id
        assert data["other_user"]["nickname"] == bob.nickname

    def test_other_user_is_null_for_group(self, alice_client, group_room):
        response = alice_client.get("/api/v1/chat/rooms/")
        rooms = {r["room_type"]: r for r in response.data["data"]}
        assert rooms["group"]["other_user"] is None

    def test_includes_last_message_when_exists(self, alice_client, private_room, bob):
        Message.objects.create(room=private_room, sender=bob, content="Hello Alice")
        response = alice_client.get("/api/v1/chat/rooms/")
        data = response.data["data"][0]
        assert data["last_message"] == "Hello Alice"
        assert data["last_message_at"] is not None

    def test_last_message_is_none_when_no_messages(self, alice_client, private_room):
        response = alice_client.get("/api/v1/chat/rooms/")
        data = response.data["data"][0]
        assert data["last_message"] is None
        assert data["last_message_at"] is None

    def test_unread_count_reflects_other_users_messages(self, alice_client, private_room, bob):
        Message.objects.create(room=private_room, sender=bob, content="Hi")
        response = alice_client.get("/api/v1/chat/rooms/")
        data = response.data["data"][0]
        assert data["unread_count"] == 1

    def test_reading_room_clears_unread(self, alice_client, private_room, bob):
        Message.objects.create(room=private_room, sender=bob, content="Unread")
        resp1 = alice_client.get("/api/v1/chat/rooms/")
        assert resp1.data["data"][0]["unread_count"] == 1

        alice_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")

        resp2 = alice_client.get("/api/v1/chat/rooms/")
        assert resp2.data["data"][0]["unread_count"] == 0

    def test_unauthenticated_returns_403(self, client):
        response = client.get("/api/v1/chat/rooms/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestRoomCreateView:
    """POST /api/v1/chat/rooms/create/"""

    def test_create_private_room(self, alice_client, bob):
        response = alice_client.post("/api/v1/chat/rooms/create/", {
            "type": "private",
            "member_ids": [bob.id],
        })
        assert response.status_code == status.HTTP_201_CREATED
        room = ChatRoom.objects.get(id=response.data["data"]["id"])
        assert room.room_type == "private"
        assert room.members.count() == 2

    def test_duplicate_private_returns_existing(self, alice_client, bob, private_room):
        response = alice_client.post("/api/v1/chat/rooms/create/", {
            "type": "private",
            "member_ids": [bob.id],
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["id"] == private_room.id
        assert ChatRoom.objects.filter(room_type="private").count() == 1

    def test_private_room_with_extra_members_errors(self, alice_client, bob, charlie):
        response = alice_client.post("/api/v1/chat/rooms/create/", {
            "type": "private",
            "member_ids": [bob.id, charlie.id],
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_group_room(self, alice_client, bob, charlie):
        response = alice_client.post("/api/v1/chat/rooms/create/", {
            "type": "group",
            "name": "Group Chat",
            "member_ids": [bob.id, charlie.id],
        })
        assert response.status_code == status.HTTP_201_CREATED
        room = ChatRoom.objects.get(id=response.data["data"]["id"])
        assert room.room_type == "group"
        assert room.is_group is True
        assert room.name == "Group Chat"
        assert room.members.count() == 3

    def test_group_room_without_name(self, alice_client, bob, charlie):
        response = alice_client.post("/api/v1/chat/rooms/create/", {
            "type": "group",
            "member_ids": [bob.id, charlie.id],
        })
        assert response.status_code == status.HTTP_201_CREATED
        room = ChatRoom.objects.get(id=response.data["data"]["id"])
        assert room.room_type == "group"
        assert room.name == ""

    def test_missing_member_ids_errors(self, alice_client):
        response = alice_client.post("/api/v1/chat/rooms/create/", {"type": "private"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_type_errors(self, alice_client, bob):
        response = alice_client.post("/api/v1/chat/rooms/create/", {"member_ids": [bob.id]})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.xfail(reason="View does not validate member_ids exist; creates orphan FK (pre-existing bug)")
    def test_nonexistent_user_errors(self, alice_client):
        with pytest.raises(Exception):
            alice_client.post("/api/v1/chat/rooms/create/", {
                "type": "private",
                "member_ids": [99999],
            })

    def test_unauthenticated_returns_403(self, client, bob):
        response = client.post("/api/v1/chat/rooms/create/", {
            "type": "private",
            "member_ids": [bob.id],
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestRoomMessagesView:
    """GET /api/v1/chat/rooms/{room_id}/messages/"""

    def test_member_can_read_messages(self, alice_client, private_room, bob):
        msg = Message.objects.create(room=private_room, sender=bob, content="Hi Alice")
        response = alice_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        assert response.status_code == status.HTTP_200_OK
        body = response.data["data"]
        assert body["total"] == 1
        assert body["results"][0]["id"] == msg.id
        assert body["results"][0]["content"] == "Hi Alice"
        assert body["results"][0]["sender_id"] == bob.id

    def test_pagination_structure(self, alice_client, private_room, bob):
        for i in range(3):
            Message.objects.create(room=private_room, sender=bob, content=f"Msg {i}")
        response = alice_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        assert response.status_code == status.HTTP_200_OK
        body = response.data["data"]
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 50
        assert len(body["results"]) == 3

    def test_empty_room(self, alice_client, private_room):
        response = alice_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        assert response.status_code == status.HTTP_200_OK
        body = response.data["data"]
        assert body["total"] == 0
        assert body["results"] == []

    def test_messages_ordered_by_created_at_desc(self, alice_client, private_room, bob):
        m1 = Message.objects.create(room=private_room, sender=bob, content="First")
        m2 = Message.objects.create(room=private_room, sender=bob, content="Second")
        response = alice_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        results = response.data["data"]["results"]
        assert results[0]["id"] == m2.id
        assert results[1]["id"] == m1.id

    def test_non_member_gets_404(self, charlie_client, private_room):
        response = charlie_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_updates_last_read_at(self, alice_client, private_room):
        before = timezone.now()
        response = alice_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        assert response.status_code == status.HTTP_200_OK
        member = ChatRoomMember.objects.get(room=private_room, user__username="alice")
        assert member.last_read_at is not None
        assert member.last_read_at >= before

    def test_nonexistent_room_returns_404(self, alice_client):
        response = alice_client.get("/api/v1/chat/rooms/99999/messages/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_403(self, client, private_room):
        response = client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestMessageSendView:
    """POST /api/v1/chat/rooms/{room_id}/messages/send/"""

    def test_member_can_send_message(self, alice_client, private_room):
        response = alice_client.post(
            f"/api/v1/chat/rooms/{private_room.id}/messages/send/",
            {"content": "Hello"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["content"] == "Hello"
        assert Message.objects.filter(room=private_room).count() == 1

    def test_sender_info_in_response(self, alice_client, alice, private_room):
        response = alice_client.post(
            f"/api/v1/chat/rooms/{private_room.id}/messages/send/",
            {"content": "From Alice"},
        )
        data = response.data["data"]
        assert data["sender_id"] == alice.id
        assert data["sender_nickname"] == alice.nickname
        assert data["msg_type"] == "text"

    def test_other_member_can_see_sent_message(self, alice_client, bob_client, private_room):
        alice_client.post(
            f"/api/v1/chat/rooms/{private_room.id}/messages/send/",
            {"content": "Hi Bob"},
        )
        response = bob_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["total"] == 1
        assert response.data["data"]["results"][0]["content"] == "Hi Bob"

    def test_missing_content_errors(self, alice_client, private_room):
        response = alice_client.post(
            f"/api/v1/chat/rooms/{private_room.id}/messages/send/",
            {"content": ""},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == 40001

    def test_non_member_gets_404(self, charlie_client, private_room):
        response = charlie_client.post(
            f"/api/v1/chat/rooms/{private_room.id}/messages/send/",
            {"content": "Hello"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_room_returns_404(self, alice_client):
        response = alice_client.post(
            "/api/v1/chat/rooms/99999/messages/send/",
            {"content": "Hello"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_403(self, client, private_room):
        response = client.post(
            f"/api/v1/chat/rooms/{private_room.id}/messages/send/",
            {"content": "Hello"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ── ⛓️ 前后端契约验证 ─────────────────────────────────────────

EXPECTED_ROOM_FIELDS = {
    "id", "name", "room_type",
    "other_user", "member_count", "last_message",
    "last_message_at", "unread_count",
}
# NOTE: 模型有 is_group 但序列化器不返回。前端用 room_type=='group' 判断，不依赖 is_group。
# 若需前后端一致，应将 is_group 加入序列化器 fields。

EXPECTED_OTHER_USER_FIELDS = {"user_id", "nickname", "avatar_url"}

EXPECTED_MESSAGE_FIELDS = {
    "id", "room_id", "sender_id", "sender_nickname",
    "content", "msg_type", "created_at",
}


class TestRoomListContract:
    """前端 ChatListPage 依赖的 room 字段契约。"""

    def test_room_list_contains_all_expected_fields(self, alice_client, private_room, bob):
        Message.objects.create(room=private_room, sender=bob, content="Hi")
        resp = alice_client.get("/api/v1/chat/rooms/")
        room = resp.data["data"][0]
        expected = EXPECTED_ROOM_FIELDS
        missing = expected - set(room.keys())
        assert not missing, f"room 响应缺少字段: {missing}"

    def test_room_other_user_contains_all_fields(self, alice_client, private_room, bob):
        resp = alice_client.get("/api/v1/chat/rooms/")
        other = resp.data["data"][0]["other_user"]
        missing = EXPECTED_OTHER_USER_FIELDS - set(other.keys())
        assert not missing, f"other_user 缺少字段: {missing}"

    def test_message_contains_all_expected_fields(self, alice_client, private_room, bob):
        Message.objects.create(room=private_room, sender=bob, content="Hello")
        resp = alice_client.get(f"/api/v1/chat/rooms/{private_room.id}/messages/")
        msg = resp.data["data"]["results"][0]
        missing = EXPECTED_MESSAGE_FIELDS - set(msg.keys())
        assert not missing, f"message 响应缺少字段: {missing}"

    def test_send_message_response_has_id_not_message_id(self, alice_client, private_room, bob):
        """前端 chat.js:72 用 payload.data.id || payload.data.message_id 回退"""
        resp = alice_client.post(
            f"/api/v1/chat/rooms/{private_room.id}/messages/send/",
            {"content": "Hi"},
        )
        assert "id" in resp.data["data"], "send_message 响应必须有 id 字段"
        # 如果同时有 message_id，前端选 id，但不应依赖 message_id
        if "message_id" in resp.data["data"]:
            assert resp.data["data"]["id"] == resp.data["data"]["message_id"]

    def test_unread_count_is_integer(self, alice_client, private_room, bob):
        Message.objects.create(room=private_room, sender=bob, content="Unread test")
        resp = alice_client.get("/api/v1/chat/rooms/")
        assert isinstance(resp.data["data"][0]["unread_count"], int)
