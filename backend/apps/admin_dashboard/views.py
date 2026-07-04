from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_dashboard.models import SiteLog, SiteSettings
from apps.admin_dashboard.serializers import (
    AdminLogSerializer,
    AdminCommentSerializer,
    AdminPostSerializer,
    AdminSiteSettingsSerializer,
    AdminSiteSettingsUpdateSerializer,
    AdminUserSerializer,
)
from apps.common.utils import api_response, safe_int
from apps.chat.models import ChatRoom, Message
from apps.feed.models import Comment, Post
from apps.groups.models import InterestGroup, GroupMember
from apps.plugins.models import Plugin
from apps.plugins.registry import PluginRegistry

User = get_user_model()


class AdminPermissionMixin:
    def check_admin(self, request):
        if not request.user.is_authenticated or not request.user.is_staff:
            return api_response(code=40003, message="无权访问", status=status.HTTP_403_FORBIDDEN)
        return None


class AdminUserListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        search = request.query_params.get("search", "").strip()
        users = User.objects.all()
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(nickname__icontains=search)
                | Q(email__icontains=search)
            )
        users = users.order_by("-date_joined")
        serializer = AdminUserSerializer(users, many=True)
        return api_response(data=serializer.data)


class AdminUserUpdateView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return api_response(code=40004, message="用户不存在", status=status.HTTP_404_NOT_FOUND)

        allowed_fields = {"is_active"}
        if request.user.is_superuser:
            allowed_fields.add("is_staff")
        updates = {key: value for key, value in request.data.items() if key in allowed_fields}
        for key, value in updates.items():
            setattr(user, key, value)
        user.save()

        SiteLog.objects.create(
            user=request.user,
            action="update_user",
            detail={"user_id": pk, "changes": request.data},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(data=AdminUserSerializer(user).data)


class AdminPostListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        posts = Post.objects.all().order_by("-created_at")
        serializer = AdminPostSerializer(posts, many=True)
        return api_response(data=serializer.data)


class AdminPostDeleteView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return api_response(code=40004, message="动态不存在", status=status.HTTP_404_NOT_FOUND)

        post.delete()

        SiteLog.objects.create(
            user=request.user,
            action="delete_post",
            detail={"post_id": pk},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(message="动态已删除")


class AdminCommentListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        comments = Comment.objects.select_related("author", "post").order_by("-created_at")
        serializer = AdminCommentSerializer(comments, many=True)
        return api_response(data=serializer.data)


class AdminCommentDeleteView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            return api_response(code=40004, message="评论不存在", status=status.HTTP_404_NOT_FOUND)

        comment.delete()

        SiteLog.objects.create(
            user=request.user,
            action="delete_comment",
            detail={"comment_id": pk},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(message="评论已删除")


class AdminAnonymousQuestionsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.questions.models import AnonymousQuestion
        from apps.plugins.questions.serializers import AdminQuestionSerializer
        questions = AnonymousQuestion.objects.all().order_by("-created_at")
        serializer = AdminQuestionSerializer(questions, many=True)
        return api_response(data=serializer.data)


class AdminQuizQuestionsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from apps.plugins.quizzes.models import QuizQuestion, QuizAnswer
        questions = QuizQuestion.objects.all().select_related("creator", "target_user")
        data = []
        for q in questions:
            answer = QuizAnswer.objects.filter(question=q).first()
            data.append({
                "id": q.id,
                "creator": {
                    "user_id": q.creator.id,
                    "nickname": q.creator.nickname,
                },
                "target_user": {
                    "user_id": q.target_user.id,
                    "nickname": q.target_user.nickname,
                },
                "question": q.question,
                "has_answer": answer is not None,
                "is_correct": answer.is_correct if answer else None,
                "created_at": q.created_at,
            })
        return api_response(data=data)


class AdminPluginListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        plugins = Plugin.objects.all()
        data = [
            {
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "is_active": p.is_active,
                "config": p.config,
                "created_at": p.created_at,
            }
            for p in plugins
        ]
        return api_response(data=data)


class AdminPluginUpdateView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            plugin = Plugin.objects.get(pk=pk)
        except Plugin.DoesNotExist:
            return api_response(code=40004, message="插件不存在", status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get("is_active")
        if is_active is not None:
            plugin.is_active = is_active
            plugin.save()

        SiteLog.objects.create(
            user=request.user,
            action="update_plugin",
            detail={"plugin_id": pk, "is_active": is_active},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(data={
            "id": plugin.id,
            "name": plugin.name,
            "type": plugin.type,
            "is_active": plugin.is_active,
            "config": plugin.config,
            "created_at": plugin.created_at,
        })


class AdminSettingsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        settings = SiteSettings.objects.all()
        serializer = AdminSiteSettingsSerializer(settings, many=True)
        return api_response(data=serializer.data)

    def patch(self, request):
        error = self.check_admin(request)
        if error:
            return error

        serializer = AdminSiteSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        settings_data = serializer.validated_data["settings"]
        for key, value in settings_data.items():
            SiteSettings.objects.update_or_create(key=key, defaults={"value": value})

        SiteLog.objects.create(
            user=request.user,
            action="update_settings",
            detail={"settings": settings_data},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        settings = SiteSettings.objects.all()
        out_serializer = AdminSiteSettingsSerializer(settings, many=True)
        return api_response(data=out_serializer.data)


class AdminStatsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        data = {
            "total_users": User.objects.count(),
            "total_posts": Post.objects.count(),
            "total_comments": Comment.objects.count(),
            "total_messages": Message.objects.count(),
            "active_users_today": User.objects.filter(last_login__date__gte=timezone.now().date()).count(),
        }
        return api_response(data=data)


class AdminPluginConfigView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        configs = []
        for plugin in PluginRegistry.get_all_plugins().values():
            admin_config = plugin.get_admin_config()
            if admin_config and admin_config.get("sidebar"):
                configs.append({
                    "type": plugin.plugin_type,
                    "name": plugin.display_name,
                    **admin_config,
                })
        return api_response(data=configs)


class AdminLogsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        logs = SiteLog.objects.all()

        action = request.query_params.get("action", "").strip()
        if action:
            logs = logs.filter(action=action)

        user_id = request.query_params.get("user_id", "").strip()
        if user_id:
            logs = logs.filter(user_id=user_id)

        logs = logs.order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 50
        total = logs.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_logs = logs[start:end]

        serializer = AdminLogSerializer(page_logs, many=True)
        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })


class AdminLogActionsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        actions = SiteLog.objects.values_list("action", flat=True).distinct().order_by("action")
        return api_response(data=list(actions))


class AdminTrendsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        from django.utils import timezone
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from apps.feed.models import Post
        from apps.accounts.models import User

        days = safe_int(request.query_params.get("days"), 7)
        since = timezone.now() - timezone.timedelta(days=days)

        user_trends = (
            User.objects.filter(date_joined__gte=since)
            .annotate(date=TruncDate("date_joined"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        post_trends = (
            Post.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        from apps.chat.models import Message
        from apps.feed.models import Comment
        from apps.profiles.models import VisitRecord
        from apps.friends.models import Friendship

        msg_trends = (
            Message.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        comment_trends = (
            Comment.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        visit_trends = (
            VisitRecord.objects.filter(visited_at__gte=since)
            .annotate(date=TruncDate("visited_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        friend_trends = (
            Friendship.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        return api_response(data={
            "days": days,
            "users": list(user_trends),
            "posts": list(post_trends),
            "messages": list(msg_trends),
            "comments": list(comment_trends),
            "visits": list(visit_trends),
            "friendships": list(friend_trends),
        })


class AdminGroupListView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error

        groups = InterestGroup.objects.annotate(member_count=Count('members'))
        search = request.query_params.get("search", "").strip()
        if search:
            groups = groups.filter(name__icontains=search)
        groups = groups.order_by("-created_at")

        data = []
        for g in groups:
            data.append({
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "cover_url": g.cover_image.url if g.cover_image else None,
                "is_public": g.is_public,
                "creator_name": g.creator.nickname,
                "member_count": g.member_count,
                "created_at": g.created_at,
            })
        return api_response(data=data)


class AdminGroupDeleteView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        group_info = {"id": group.id, "name": group.name, "creator": group.creator.nickname}

        GroupMember.objects.filter(group=group).delete()
        ChatRoom.objects.filter(group_id=pk).delete()
        Post.objects.filter(group_id=pk).update(group=None)
        group.delete()

        SiteLog.objects.create(
            user=request.user,
            action="delete_group",
            detail=group_info,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(message="小组已删除")


class AdminGroupPostsView(APIView, AdminPermissionMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error

        try:
            group = InterestGroup.objects.get(pk=pk)
        except InterestGroup.DoesNotExist:
            return api_response(code=40004, message="小组不存在", status=status.HTTP_404_NOT_FOUND)

        posts = Post.objects.filter(group_id=pk).select_related('author').order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = posts.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_posts = posts[start:end]

        results = []
        for p in page_posts:
            results.append({
                "id": p.id,
                "author_name": p.author.nickname,
                "content": p.content,
                "created_at": p.created_at,
            })

        return api_response(data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results,
        })
