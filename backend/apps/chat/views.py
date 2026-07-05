from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.models import ChatRoom, ChatRoomMember, Message
from apps.chat.serializers import (
    ChatRoomListSerializer,
    MessageSerializer,
    RoomCreateSerializer,
)
from apps.common.utils import api_response, safe_int


class RoomListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        last_message = Message.objects.filter(room_id=OuterRef("id")).order_by("-created_at")
        rooms = ChatRoom.objects.filter(members__user=request.user).prefetch_related(
            Prefetch("members", queryset=ChatRoomMember.objects.select_related("user")),
        ).annotate(
            _last_msg_content=Subquery(last_message.values("content")[:1]),
            _last_msg_at=Subquery(last_message.values("created_at")[:1]),
        ).order_by("-created_at")
        serializer = ChatRoomListSerializer(rooms, many=True, context={"request": request})
        return api_response(data=serializer.data)

    def post(self, request):
        return RoomCreateView.as_view()(request)


class RoomMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id):
        try:
            room = ChatRoom.objects.get(id=room_id, members__user=request.user)
        except ChatRoom.DoesNotExist:
            return api_response(
                code=40004,
                message="房间不存在或无权访问",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = room.messages.select_related("sender")
        page = safe_int(request.query_params.get("page"), 1)
        page_size = 50
        start = (page - 1) * page_size
        end = start + page_size
        total = messages.count()
        page_messages = messages.order_by("-created_at")[start:end]

        serializer = MessageSerializer(page_messages, many=True)
        ChatRoomMember.objects.filter(room=room, user=request.user).update(last_read_at=timezone.now())
        return api_response(
            data={
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        )

    def post(self, request, room_id):
        return MessageSendView.as_view()(request, room_id=room_id)


class RoomCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room_type = serializer.validated_data["type"]
        name = serializer.validated_data.get("name", "")
        member_ids = serializer.validated_data["member_ids"]

        user = request.user
        all_member_ids = list(set(member_ids + [user.id]))

        if room_type == "private":
            if len(all_member_ids) != 2:
                return api_response(
                    code=40001,
                    message="私聊必须恰好两名成员",
                    data=None,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing = ChatRoom.objects.filter(
                room_type="private", members__user_id=all_member_ids[0]
            ).filter(members__user_id=all_member_ids[1])
            if existing.exists():
                room = existing.first()
                serializer = ChatRoomListSerializer(room, context={"request": request})
                return api_response(data=serializer.data)

        room = ChatRoom.objects.create(
            name=name,
            is_group=(room_type == "group"),
            room_type=room_type,
        )

        for uid in all_member_ids:
            ChatRoomMember.objects.create(room=room, user_id=uid)

        result = ChatRoomListSerializer(room, context={"request": request})
        return api_response(data=result.data, status=status.HTTP_201_CREATED)


class MessageSendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        try:
            room = ChatRoom.objects.get(id=room_id, members__user=request.user)
        except ChatRoom.DoesNotExist:
            return api_response(
                code=40004,
                message="房间不存在或无权访问",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        content = request.data.get("content", "").strip()
        msg_type = request.data.get("msg_type", "text")

        if not content:
            return api_response(
                code=40001,
                message="消息内容不能为空",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = Message.objects.create(
            room=room,
            sender=request.user,
            content=content,
            msg_type=msg_type,
        )

        serialized_message = MessageSerializer(message).data
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"chat_{room.id}",
                {
                    "type": "chat_message",
                    "message": dict(serialized_message),
                },
            )

        return api_response(
            data=serialized_message,
            status=status.HTTP_201_CREATED,
        )
