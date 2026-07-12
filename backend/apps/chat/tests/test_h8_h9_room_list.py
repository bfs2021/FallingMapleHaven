import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import ChatRoom, ChatRoomMember, Message

User = get_user_model()


@pytest.mark.django_db
class TestH8H9RoomList:
    def test_room_list_returns_last_message(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        room = ChatRoom.objects.create(room_type="private")
        ChatRoomMember.objects.create(room=room, user=alice)
        ChatRoomMember.objects.create(room=room, user=bob)
        Message.objects.create(room=room, sender=alice, content="Old")
        Message.objects.create(room=room, sender=alice, content="Latest!")
        client.force_authenticate(user=alice)
        response = client.get("/api/v1/chat/rooms/")
        assert response.status_code == status.HTTP_200_OK
        rooms = response.data["data"]
        assert len(rooms) == 1
        assert rooms[0]["last_message"] == "Latest!"

    def test_room_list_no_messages_returns_none(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        room = ChatRoom.objects.create(room_type="private")
        ChatRoomMember.objects.create(room=room, user=alice)
        ChatRoomMember.objects.create(room=room, user=bob)
        client.force_authenticate(user=alice)
        response = client.get("/api/v1/chat/rooms/")
        assert response.status_code == status.HTTP_200_OK
        rooms = response.data["data"]
        assert len(rooms) == 1
        assert rooms[0]["last_message"] is None

    def test_room_list_multiple_rooms(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        charlie = User.objects.create_user(username="charlie", password="pass")
        room1 = ChatRoom.objects.create(room_type="private")
        ChatRoomMember.objects.create(room=room1, user=alice)
        ChatRoomMember.objects.create(room=room1, user=bob)
        room2 = ChatRoom.objects.create(room_type="private")
        ChatRoomMember.objects.create(room=room2, user=alice)
        ChatRoomMember.objects.create(room=room2, user=charlie)
        Message.objects.create(room=room1, sender=bob, content="Hello from Bob")
        Message.objects.create(room=room2, sender=charlie, content="Hi from Charlie")
        client.force_authenticate(user=alice)
        response = client.get("/api/v1/chat/rooms/")
        assert response.status_code == status.HTTP_200_OK
        rooms = response.data["data"]
        assert len(rooms) == 2
        messages = {room["last_message"] for room in rooms}
        assert "Hello from Bob" in messages
        assert "Hi from Charlie" in messages
