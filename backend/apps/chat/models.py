from django.conf import settings
from django.db import models


class ChatRoom(models.Model):
    class Type(models.TextChoices):
        PRIVATE = "private", "私聊"
        GROUP = "group", "群聊"

    name = models.CharField(max_length=100, blank=True, null=True)
    is_group = models.BooleanField(default=False)
    room_type = models.CharField(max_length=10, choices=Type.choices, default=Type.PRIVATE)
    group = models.ForeignKey(
        "groups.InterestGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_chatroom"

    def __str__(self):
        return self.name or f"ChatRoom {self.id}"


class ChatRoomMember(models.Model):
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chat_chatroommember"
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user"], name="uq_chat_room_member"
            )
        ]

    def __str__(self):
        return f"{self.user.username} in room {self.room_id}"


class Message(models.Model):
    class MsgType(models.TextChoices):
        TEXT = "text", "文本"
        IMAGE = "image", "图片"
        FILE = "file", "文件"
        SYSTEM = "system", "系统"

    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    content = models.TextField()
    msg_type = models.CharField(max_length=10, choices=MsgType.choices, default=MsgType.TEXT)
    file = models.FileField(upload_to="chat/files/", null=True, blank=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at"]

    def __str__(self):
        return f"Message by {self.sender.username}"


class MessageRead(models.Model):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="reads"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_messageread"
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"], name="uq_chat_message_read"
            )
        ]

    def __str__(self):
        return f"Read by {self.user.username}"
