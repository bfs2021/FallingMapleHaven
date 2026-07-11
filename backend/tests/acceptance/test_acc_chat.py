import pytest
from rest_framework import status

BASE = "/api/v1/chat/"

pytestmark = pytest.mark.django_db


def _send_message(client, room_id, content, msg_type="text"):
    return client.post(
        f"{BASE}rooms/{room_id}/messages/send/",
        {"content": content, "msg_type": msg_type},
    )


class TestRoomList:
    """GET /chat/rooms/ — PRD §2.4"""

    def test_room_list_shows_all_user_rooms(self, alice_client, private_room, group_room):
        resp = alice_client.get(BASE + "rooms/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", [])
        room_ids = [r["id"] for r in data]
        assert private_room.id in room_ids
        assert group_room.id in room_ids

    def test_room_list_includes_other_user_for_private(self, alice_client, bob, private_room):
        resp = alice_client.get(BASE + "rooms/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", [])
        room = next(r for r in data if r["id"] == private_room.id)
        assert room["room_type"] == "private"
        assert room["other_user"] is not None
        assert room["other_user"]["user_id"] == bob.id
        assert room["other_user"]["nickname"] == bob.nickname
        assert "avatar_url" in room["other_user"]

    def test_unauthenticated_room_list_rejected(self, client):
        resp = client.get(BASE + "rooms/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_room_list_unread_depends_on_last_read(self, alice_client, bob_client, private_room):
        bob_client.post(
            f"{BASE}rooms/{private_room.id}/messages/send/",
            {"content": "Hello from Bob", "msg_type": "text"},
        )
        resp = alice_client.get(BASE + "rooms/")
        data = resp.data.get("data", [])
        room = next(r for r in data if r["id"] == private_room.id)
        assert room["unread_count"] >= 1
        assert room["last_message"] == "Hello from Bob"
        assert room["last_message_at"] is not None


class TestCreatePrivateRoom:
    """POST /chat/rooms/create/ — PRD §2.4.1"""

    def test_create_private_room_returns_room_id(self, alice_client, charlie):
        resp = alice_client.post(
            BASE + "rooms/create/",
            {"type": "private", "member_ids": [charlie.id]},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data.get("data", {})
        assert data.get("id") is not None

    def test_reuses_existing_private_room(self, alice_client, bob, private_room):
        resp = alice_client.post(
            BASE + "rooms/create/",
            {"type": "private", "member_ids": [bob.id]},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", {})
        assert data["id"] == private_room.id

    def test_create_private_with_non_friend(self, alice_client, charlie):
        resp = alice_client.post(
            BASE + "rooms/create/",
            {"type": "private", "member_ids": [charlie.id]},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data.get("data", {})
        assert data.get("id") is not None

    def test_create_private_requires_auth(self, client, charlie):
        resp = client.post(
            BASE + "rooms/create/",
            {"type": "private", "member_ids": [charlie.id]},
        )
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestSendMessage:
    """POST /chat/rooms/{id}/messages/send/ — PRD §2.4"""

    def test_send_text_message(self, alice_client, private_room, alice):
        resp = _send_message(alice_client, private_room.id, "Hello!")
        assert resp.status_code == status.HTTP_201_CREATED
        msg = resp.data.get("data", {})
        assert msg["content"] == "Hello!"
        assert msg["msg_type"] == "text"
        assert msg["sender_id"] == alice.id
        assert msg["room_id"] == private_room.id
        assert msg.get("sender_nickname") is not None
        assert "created_at" in msg

    def test_send_message_requires_membership(self, charlie_client, private_room):
        resp = _send_message(charlie_client, private_room.id, "Hack attempt")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_send_message_empty_content_rejected(self, alice_client, private_room):
        resp = _send_message(alice_client, private_room.id, "")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_message_requires_auth(self, client, private_room):
        resp = _send_message(client, private_room.id, "Hello")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestMessageHistory:
    """GET /chat/rooms/{id}/messages/ — PRD §2.4.3"""

    def test_message_history_pagination(self, alice_client, private_room, bob_client):
        for i in range(5):
            bob_client.post(
                f"{BASE}rooms/{private_room.id}/messages/send/",
                {"content": f"Message {i}", "msg_type": "text"},
            )
        resp = alice_client.get(f"{BASE}rooms/{private_room.id}/messages/", {"page": 1})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data", {})
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert data["total"] == 5
        assert len(data["results"]) == 5

    def test_message_history_requires_membership(self, charlie_client, private_room):
        resp = charlie_client.get(f"{BASE}rooms/{private_room.id}/messages/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_message_history_requires_auth(self, client, private_room):
        resp = client.get(f"{BASE}rooms/{private_room.id}/messages/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)