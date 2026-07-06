from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.common.utils import api_response
from apps.friends.models import Friendship
from apps.friends.serializers import (
    FriendHandleSerializer,
    FriendRequestReceivedSerializer,
    FriendRequestSerializer,
    FriendSerializer,
    UnfriendSerializer,
    UserSearchSerializer,
)


class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FriendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_user_id = serializer.validated_data["to_user_id"]
        if to_user_id == request.user.id:
            return api_response(
                code=40001,
                message="不能添加自己为好友",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not User.objects.filter(id=to_user_id).exists():
            return api_response(
                code=40004,
                message="用户不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        existing = Friendship.objects.filter(
            Q(from_user=request.user, to_user_id=to_user_id)
            | Q(from_user_id=to_user_id, to_user=request.user),
            status__in=[Friendship.Status.PENDING, Friendship.Status.ACCEPTED],
        ).first()
        if existing:
            if existing.status == Friendship.Status.ACCEPTED:
                msg = "已是好友"
            else:
                msg = "已发送过好友申请，请等待对方确认"
            return api_response(
                code=40001,
                message=msg,
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        friendship, created = Friendship.objects.get_or_create(
            from_user=request.user, to_user_id=to_user_id,
            defaults={"status": Friendship.Status.PENDING},
        )
        if not created:
            if friendship.status == Friendship.Status.ACCEPTED:
                return api_response(code=40001, message="已是好友", data=None, status=status.HTTP_400_BAD_REQUEST)
            if friendship.status == Friendship.Status.PENDING:
                return api_response(code=40001, message="已发送过好友申请", data=None, status=status.HTTP_400_BAD_REQUEST)
            friendship.status = Friendship.Status.PENDING
            friendship.save()
        return api_response(message="好友申请已发送", status=status.HTTP_201_CREATED)


class FriendHandleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FriendHandleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_id = serializer.validated_data.get("request_id")
        from_user_id = serializer.validated_data.get("from_user_id")
        action = serializer.validated_data["action"]

        try:
            if request_id:
                friendship = Friendship.objects.get(
                    id=request_id, to_user=request.user, status=Friendship.Status.PENDING
                )
            elif from_user_id:
                friendship = Friendship.objects.get(
                    from_user_id=from_user_id, to_user=request.user, status=Friendship.Status.PENDING
                )
            else:
                return api_response(code=40001, message="缺少请求参数", data=None, status=status.HTTP_400_BAD_REQUEST)
        except Friendship.DoesNotExist:
            return api_response(
                code=40004,
                message="申请不存在或已处理",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        if action == "accept":
            friendship.status = Friendship.Status.ACCEPTED
            friendship.save()
            return api_response(message="好友请求已接受")
        else:
            friendship.status = Friendship.Status.REJECTED
            friendship.save()
            return api_response(message="好友请求已拒绝")


class UnfriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UnfriendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        friend_id = serializer.validated_data["friend_id"]
        deleted, _ = Friendship.objects.filter(
            Q(from_user=request.user, to_user_id=friend_id)
            | Q(from_user_id=friend_id, to_user=request.user),
            status=Friendship.Status.ACCEPTED,
        ).delete()

        if deleted == 0:
            return api_response(
                code=40004,
                message="好友关系不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )
        return api_response(message="已解除好友关系")


class FriendListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friendships = Friendship.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user),
            status=Friendship.Status.ACCEPTED,
        ).order_by("from_user__nickname", "to_user__nickname")
        serializer = FriendSerializer(friendships, many=True, context={"request": request})
        return api_response(data=serializer.data)


class FriendRequestReceivedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests = Friendship.objects.filter(
            to_user=request.user, status=Friendship.Status.PENDING
        )
        serializer = FriendRequestReceivedSerializer(requests, many=True)
        return api_response(data=serializer.data)


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return api_response(data=[])
        users = User.objects.filter(
            Q(username__icontains=q) | Q(nickname__icontains=q)
        ).exclude(id=request.user.id)[:10]
        serializer = UserSearchSerializer(users, many=True)
        return api_response(data=serializer.data)
