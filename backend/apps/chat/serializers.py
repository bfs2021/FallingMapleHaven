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

    def _cached_last_msg(self, obj):
        cache = getattr(self, '_msg_cache', {})
        if obj.id not in cache:
            cache[obj.id] = obj.messages.order_by("-created_at").first()
            self._msg_cache = cache
        return cache[obj.id]

    def _cached_other_member(self, obj, request):
        cache = getattr(self, '_member_cache', {})
        if obj.id not in cache:
            other = None
            for m in obj.members.all():
                if m.user_id != request.user.id:
                    other = m
                    break
            cache[obj.id] = other
            self._member_cache = cache
        return cache[obj.id]

    def get_name(self, obj):
        request = self.context.get("request")
        if obj.type == "private" and request:
            other = self._cached_other_member(obj, request)
            return other.user.nickname if other else "已解散"
        return obj.name

    def get_last_message(self, obj):
        msg = self._cached_last_msg(obj)
        return msg.content if msg else None

    def get_last_message_at(self, obj):
        msg = self._cached_last_msg(obj)
        return msg.created_at if msg else None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request:
            return 0
        member = None
        for m in obj.members.all():
            if m.user_id == request.user.id:
                member = m
                break
        if member:
            last_read = member.last_read_at or member.joined_at
            return obj.messages.filter(created_at__gt=last_read).exclude(sender=request.user).count()
        return 0

    def get_other_user(self, obj):
        request = self.context.get("request")
        if obj.type == "private" and request:
            other = self._cached_other_member(obj, request)
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
