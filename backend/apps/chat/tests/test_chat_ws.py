import json

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.urls import re_path

from apps.chat.consumers import ChatConsumer

application = URLRouter([
    re_path(r"ws/chat/$", ChatConsumer.as_asgi()),
])


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestChatConsumerConnect:
    """WebSocket connection-level tests."""

    async def test_authenticated_user_can_connect(self, alice, private_room):
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        communicator.scope["user"] = alice
        communicator.scope["headers"] = [(b"origin", b"http://localhost:5173")]
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_unauthenticated_user_rejected(self, private_room):
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        communicator.scope["headers"] = [(b"origin", b"http://localhost:5173")]
        connected, _ = await communicator.connect()
        assert not connected

    async def test_authenticated_user_without_rooms_still_connects(self, alice):
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        communicator.scope["user"] = alice
        communicator.scope["headers"] = [(b"origin", b"http://localhost:5173")]
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestChatConsumerSendMessage:
    """WebSocket send_message flow tests."""

    async def test_send_message_saves_to_db(self, alice, private_room):
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        communicator.scope["user"] = alice
        communicator.scope["headers"] = [(b"origin", b"http://localhost:5173")]
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({
            "type": "send_message",
            "room_id": private_room.id,
            "content": "Hello via WS",
        })
        await communicator.disconnect()

        from channels.db import database_sync_to_async
        from apps.chat.models import Message

        count = await database_sync_to_async(Message.objects.filter(room=private_room).count)()
        assert count == 1

        msg = await database_sync_to_async(Message.objects.get)(room=private_room)
        assert msg.content == "Hello via WS"
        assert msg.sender_id == alice.id
        assert msg.msg_type == "text"

    async def test_empty_content_does_not_save(self, alice, private_room):
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        communicator.scope["user"] = alice
        communicator.scope["headers"] = [(b"origin", b"http://localhost:5173")]
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({
            "type": "send_message",
            "room_id": private_room.id,
            "content": "",
        })
        await communicator.disconnect()

        from channels.db import database_sync_to_async
        from apps.chat.models import Message

        count = await database_sync_to_async(Message.objects.filter(room=private_room).count)()
        assert count == 0

    async def test_send_to_nonexistent_room_does_not_save(self, alice):
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        communicator.scope["user"] = alice
        communicator.scope["headers"] = [(b"origin", b"http://localhost:5173")]
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({
            "type": "send_message",
            "room_id": 99999,
            "content": "Nowhere",
        })
        await communicator.disconnect()

        from channels.db import database_sync_to_async
        from apps.chat.models import Message

        count = await database_sync_to_async(Message.objects.count)()
        assert count == 0
