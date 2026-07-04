from django.utils import timezone
from rest_framework import serializers
from apps.chat.models import ChatRoom, ChatRoomMember, Message


class ChatRoomListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ["id", "name", "type", "last_message", "last_message_at", "unread_count", "other_user", "member_count"]

    def get_name(self, obj):
        request = self.context.get("request")
        if obj.type == "private" and request:
            other = obj.members.exclude(user_id=request.user.id).first()
            return other.user.nickname if other else "已解散"
        return obj.name

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        return msg.content if msg else None

    def get_last_message_at(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        return msg.created_at if msg else None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request:
            return 0
        try:
            member = obj.members.get(user_id=request.user.id)
            last_read = member.last_read_at or member.joined_at
            return obj.messages.filter(created_at__gt=last_read).exclude(sender=request.user).count()
        except ChatRoomMember.DoesNotExist:
            return 0

    def get_other_user(self, obj):
        request = self.context.get("request")
        if obj.type == "private" and request:
            other = obj.members.exclude(user_id=request.user.id).first()
            if other:
                return {
                    "user_id": other.user.id,
                    "nickname": other.user.nickname,
                    "avatar_url": other.user.avatar.url if other.user.avatar else None,
                }
        return None

    def get_member_count(self, obj):
        if obj.type == "group" and obj.group:
            return obj.group.members.count()
        return None


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source="sender.id")
    sender_nickname = serializers.CharField(source="sender.nickname")
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "room_id", "sender_id", "sender_nickname", "sender_avatar", "content", "msg_type", "created_at"]

    def get_sender_avatar(self, obj):
        return obj.sender.avatar.url if obj.sender.avatar else None


class RoomCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["private", "group"])
    name = serializers.CharField(required=False, allow_blank=True)
    member_ids = serializers.ListField(child=serializers.IntegerField())
