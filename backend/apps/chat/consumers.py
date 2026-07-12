import json
from urllib.parse import urlparse

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.chat.models import ChatRoom, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_groups = []

        origin = None
        for key, value in self.scope.get("headers", []):
            if key == b"origin":
                origin = value.decode()
                break
        if origin is None:
            await self.close()
            return
        allowed = False
        for host in settings.ALLOWED_HOSTS:
            if host == "*":
                allowed = True
                break
            parsed = urlparse(origin)
            hostname = parsed.hostname or ""
            if hostname == host or hostname.endswith("." + host):
                allowed = True
                break
        if not allowed:
            await self.close()
            return

        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        room_ids = await self.get_user_room_ids()
        for room_id in room_ids:
            group_name = f"chat_{room_id}"
            self.room_groups.append(group_name)
            await self.channel_layer.group_add(group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        for group_name in self.room_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "send_message":
            room_id = data.get("room_id")
            content = (data.get("content") or "").strip()
            if not content:
                return
            if len(content) > 2000:
                content = content[:2000]
            msg_type_value = data.get("msg_type", "text")

            message = await self.save_message(room_id, content, msg_type_value)

            if message:
                await self.channel_layer.group_send(
                    f"chat_{room_id}",
                    {
                        "type": "chat_message",
                        "message": message,
                    },
                )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "new_message",
            "data": event["message"],
        }))

    @database_sync_to_async
    def get_user_room_ids(self):
        return list(
            ChatRoom.objects.filter(members__user=self.user).values_list("id", flat=True)
        )

    @database_sync_to_async
    def save_message(self, room_id, content, msg_type):
        try:
            room = ChatRoom.objects.get(id=room_id, members__user=self.user)
        except ChatRoom.DoesNotExist:
            return None
        msg = Message.objects.create(
            room=room,
            sender=self.user,
            content=content,
            msg_type=msg_type,
        )
        return {
            "id": msg.id,
            "room_id": msg.room_id,
            "sender_id": msg.sender_id,
            "sender_nickname": self.user.nickname,
            "sender_avatar": self.user.avatar.url if self.user.avatar else None,
            "content": msg.content,
            "msg_type": msg.msg_type,
            "created_at": msg.created_at.isoformat(),
        }
