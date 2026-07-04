from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.groups.models import GroupJoinRequest, GroupMember, InterestGroup
from apps.groups.serializers import (
    GroupCreateSerializer,
    GroupDetailSerializer,
    GroupJoinRequestSerializer,
    GroupListSerializer,
    GroupMemberSerializer,
    GroupUpdateSerializer,
)
from apps.common.utils import api_response, safe_int
from apps.chat.models import ChatRoom, ChatRoomMember
from apps.feed.models import Post
from apps.feed.serializers import PostSerializer
from apps.notifications.models import Notification


class GroupListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        base_qs = InterestGroup.objects.annotate(member_count=Count('members'))
        if request.user.is_authenticated:
            groups = base_qs.annotate(
                _is_member=Exists(
                    GroupMember.objects.filter(group=OuterRef('pk'), user=request.user)
                )
            ).order_by("-created_at")
        else:
            groups = base_qs.filter(is_public=True).order_by("-created_at")
        serializer = GroupListSerializer(groups, many=True, context={"request": request})
        return api_response(data=serializer.data)


class GroupCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save(creator=request.user)
        GroupMember.objects.create(group=group, user=request.user, role="admin")

        room = ChatRoom.objects.create(
            name=group.name,
            room_type=ChatRoom.Type.GROUP,
            is_group=True,
            group=group,
        )
        ChatRoomMember.objects.create(room=room, user=request.user)

        return api_response(
            data=GroupListSerializer(group, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class GroupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            group = InterestGroup.objects.select_related('creator').prefetch_related(
                Prefetch('members', queryset=GroupMember.objects.select_related('user'))
            ).get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        serializer = GroupDetailSerializer(group, context={"request": request})
        return api_response(data=serializer.data)


class GroupUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        membership = GroupMember.objects.filter(group=group, user=request.user).first()
        if not membership or request.user != group.creator:
            return api_response(code=40003, message="无权修改小组信息", status=status.HTTP_403_FORBIDDEN)

        serializer = GroupUpdateSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(data=GroupDetailSerializer(group, context={"request": request}).data)


class GroupJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        if GroupMember.objects.filter(group=group, user=request.user).exists():
            return api_response(code=40001, message="已经是小组成员", status=status.HTTP_400_BAD_REQUEST)

        if not group.is_public:
            existing_request = GroupJoinRequest.objects.filter(group=group, applicant=request.user).first()
            if existing_request:
                if existing_request.status == GroupJoinRequest.Status.PENDING:
                    return api_response(code=40001, message="已有待处理的申请", status=status.HTTP_400_BAD_REQUEST)
                existing_request.delete()

            join_request = GroupJoinRequest.objects.create(group=group, applicant=request.user)

            admin_members = GroupMember.objects.filter(group=group, role="admin").select_related("user")
            for admin in admin_members:
                Notification.objects.create(
                    recipient=admin.user,
                    sender=request.user,
                    type="group_join_request",
                    title="加入小组申请",
                    content=f"{request.user.nickname} 申请加入 {group.name}",
                    link=f"/groups/{group.id}",
                )

            return api_response(message="申请已发送，等待组长审核")

        GroupMember.objects.create(group=group, user=request.user)

        room = ChatRoom.objects.filter(group=group).first()
        if room and not ChatRoomMember.objects.filter(room=room, user=request.user).exists():
            ChatRoomMember.objects.create(room=room, user=request.user)

        other_members = GroupMember.objects.filter(group=group).exclude(user=request.user).select_related("user")
        Notification.objects.bulk_create([
            Notification(
                recipient=m.user,
                sender=request.user,
                type="group_member_joined",
                title="新成员加入",
                content=f"欢迎 {request.user.nickname} 加入 {group.name}",
                link=f"/groups/{group.id}",
            )
            for m in other_members
        ])

        return api_response(message="加入成功")


class GroupLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        membership = GroupMember.objects.filter(group=group, user=request.user).first()
        if not membership:
            return api_response(code=40001, message="不是小组成员", status=status.HTTP_400_BAD_REQUEST)

        if membership.user == group.creator:
            return api_response(code=40003, message="群主不能退出小组", status=status.HTTP_403_FORBIDDEN)

        membership.delete()

        room = ChatRoom.objects.filter(group=group).first()
        if room:
            ChatRoomMember.objects.filter(room=room, user=request.user).delete()

        return api_response(message="已退出小组")


class GroupMemberManageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, user_id):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        membership = GroupMember.objects.filter(group=group, user=request.user).first()
        if not membership or membership.role != "admin":
            return api_response(code=40003, message="无权管理成员", status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action")
        if action not in ("remove", "promote_admin", "demote_admin"):
            return api_response(code=40001, message="无效操作", status=status.HTTP_400_BAD_REQUEST)

        target = GroupMember.objects.filter(group=group, user_id=user_id).first()
        if not target:
            return api_response(code=40004, message="目标用户不是小组成员", status=status.HTTP_404_NOT_FOUND)

        if target.user == group.creator:
            return api_response(code=40003, message="无法操作群主", status=status.HTTP_403_FORBIDDEN)

        is_owner = request.user == group.creator

        if action in ("promote_admin", "demote_admin") and not is_owner:
            return api_response(code=40003, message="无权管理管理员", status=status.HTTP_403_FORBIDDEN)

        if action == "remove" and not is_owner and target.role == "admin":
            return api_response(code=40003, message="无权移除管理员", status=status.HTTP_403_FORBIDDEN)

        if action == "remove":
            target.delete()

            room = ChatRoom.objects.filter(group=group).first()
            if room:
                ChatRoomMember.objects.filter(room=room, user_id=user_id).delete()

            return api_response(message="已移除成员")

        if action == "promote_admin":
            target.role = "admin"
            target.save()
            return api_response(message="已设为管理员")

        if action == "demote_admin":
            target.role = "member"
            target.save()
            return api_response(message="已取消管理员")

        return api_response(code=40001, message="无效操作", status=status.HTTP_400_BAD_REQUEST)


class GroupPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        if not group.members.filter(user_id=request.user.id).exists():
            return api_response(code=40003, message="仅成员可查看组内动态", status=status.HTTP_403_FORBIDDEN)

        posts = Post.objects.filter(group_id=pk).select_related("author", "group").prefetch_related("images", "comments", "likes").order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        total = posts.count()
        page_posts = posts[start:end]

        serializer = PostSerializer(page_posts, many=True, context={"request": request})
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })


class GroupDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        membership = GroupMember.objects.filter(group=group, user=request.user).first()
        if not membership or request.user != group.creator:
            return api_response(code=40003, message="无权解散小组", status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            GroupMember.objects.filter(group=group).delete()
            ChatRoom.objects.filter(group_id=pk).delete()
            Post.objects.filter(group_id=pk).update(group=None)
            group.delete()

        return api_response(message="小组已解散")


class GroupTransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        membership = GroupMember.objects.filter(group=group, user=request.user).first()
        if not membership or request.user != group.creator:
            return api_response(code=40003, message="无权转让小组", status=status.HTTP_403_FORBIDDEN)

        new_owner_id = request.data.get("new_owner_id")
        if not new_owner_id:
            return api_response(code=40001, message="请指定新群主", status=status.HTTP_400_BAD_REQUEST)

        new_owner_membership = GroupMember.objects.filter(group=group, user_id=new_owner_id).first()
        if not new_owner_membership:
            return api_response(code=40001, message="该用户不是小组成员", status=status.HTTP_400_BAD_REQUEST)

        if new_owner_membership.user == group.creator:
            return api_response(code=40001, message="不能转让给自己", status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            membership.role = "member"
            membership.save()
            new_owner_membership.role = "admin"
            new_owner_membership.save()
            group.creator = new_owner_membership.user
            group.save()

        return api_response(
            data=GroupDetailSerializer(group, context={"request": request}).data
        )


class GroupJoinRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        membership = GroupMember.objects.filter(group=group, user=request.user).first()
        if not membership or membership.role != "admin":
            return api_response(code=40003, message="无权查看申请列表", status=status.HTTP_403_FORBIDDEN)

        requests = GroupJoinRequest.objects.filter(group=group, status=GroupJoinRequest.Status.PENDING).order_by("-created_at")
        serializer = GroupJoinRequestSerializer(requests, many=True)
        return api_response(data=serializer.data)


class GroupJoinRequestHandleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, request_id):
        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        membership = GroupMember.objects.filter(group=group, user=request.user).first()
        if not membership or membership.role != "admin":
            return api_response(code=40003, message="无权处理申请", status=status.HTTP_403_FORBIDDEN)

        try:
            join_request = GroupJoinRequest.objects.get(pk=request_id, group=group)
        except GroupJoinRequest.DoesNotExist:
            return api_response(code=40004, message="申请不存在", status=status.HTTP_404_NOT_FOUND)

        if join_request.status != GroupJoinRequest.Status.PENDING:
            return api_response(code=40001, message="该申请已处理", status=status.HTTP_400_BAD_REQUEST)

        action = request.data.get("action")
        if action not in ("approved", "rejected"):
            return api_response(code=40001, message="无效操作", status=status.HTTP_400_BAD_REQUEST)

        applicant = join_request.applicant

        if action == "approved":
            GroupMember.objects.create(group=group, user=applicant)

            room = ChatRoom.objects.filter(group=group).first()
            if room and not ChatRoomMember.objects.filter(room=room, user=applicant).exists():
                ChatRoomMember.objects.create(room=room, user=applicant)

            join_request.status = GroupJoinRequest.Status.APPROVED

            Notification.objects.create(
                recipient=applicant,
                sender=request.user,
                type="group_request_approved",
                title="加入申请已通过",
                content=f"你的加入 {group.name} 申请已通过",
                link=f"/groups/{group.id}",
            )

            all_members = GroupMember.objects.filter(group=group).exclude(user=applicant).select_related("user")
            Notification.objects.bulk_create([
                Notification(
                    recipient=m.user,
                    sender=applicant,
                    type="group_member_joined",
                    title="新成员加入",
                    content=f"欢迎 {applicant.nickname} 加入 {group.name}",
                    link=f"/groups/{group.id}",
                )
                for m in all_members
            ])
        else:
            join_request.status = GroupJoinRequest.Status.REJECTED

            Notification.objects.create(
                recipient=applicant,
                sender=request.user,
                type="group_request_rejected",
                title="加入申请已拒绝",
                content=f"你的加入 {group.name} 申请已被拒绝",
                link="",
            )

        join_request.handled_by = request.user
        join_request.handled_at = timezone.now()
        join_request.save()

        return api_response(message="操作成功")
