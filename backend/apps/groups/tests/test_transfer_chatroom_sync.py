import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import ChatRoom, ChatRoomMember
from apps.groups.models import InterestGroup, GroupMember

User = get_user_model()


@pytest.mark.django_db
class TestGroupTransferChatRoomSync:
    def test_transfer_adds_new_owner_to_chatroom(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=True)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        GroupMember.objects.create(group=group, user=bob, role="member")
        room = ChatRoom.objects.create(
            name=group.name, room_type=ChatRoom.Type.GROUP, group=group
        )
        ChatRoomMember.objects.create(room=room, user=alice)
        client.force_authenticate(user=alice)
        response = client.post(
            f"/api/v1/groups/{group.id}/transfer/",
            {"new_owner_id": bob.id},
        )
        assert response.status_code == status.HTTP_200_OK
        assert ChatRoomMember.objects.filter(room=room, user=bob).exists()

    def test_transfer_idempotent_when_already_member(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=True)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        GroupMember.objects.create(group=group, user=bob, role="member")
        room = ChatRoom.objects.create(
            name=group.name, room_type=ChatRoom.Type.GROUP, group=group
        )
        ChatRoomMember.objects.create(room=room, user=alice)
        ChatRoomMember.objects.create(room=room, user=bob)
        client.force_authenticate(user=alice)
        response = client.post(
            f"/api/v1/groups/{group.id}/transfer/",
            {"new_owner_id": bob.id},
        )
        assert response.status_code == status.HTTP_200_OK
        assert ChatRoomMember.objects.filter(room=room, user=bob).count() == 1
