from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.feed.models import Post
from apps.friends.models import Friendship
from apps.profiles.models import GuestbookEntry, UserProfile, VisitRecord
from apps.common.utils import api_response, safe_int
from apps.profiles.serializers import (
    GuestbookCreateSerializer,
    GuestbookEntrySerializer,
    GuestbookReplySerializer,
    ProfileSerializer,
    VisitorSerializer,
)


def get_friend_status(request_user, target_user):
    if request_user == target_user:
        return "self"
    friendship = Friendship.objects.filter(
        Q(from_user=request_user, to_user=target_user)
        | Q(from_user=target_user, to_user=request_user),
        status__in=[Friendship.Status.PENDING, Friendship.Status.ACCEPTED],
    ).first()
    if not friendship:
        return "none"
    if friendship.status == Friendship.Status.ACCEPTED:
        return "accepted"
    if friendship.from_user == request_user:
        return "pending_sent"
    return "pending_received"


def resolve_profile_user(username_or_id, lookup=None):
    if lookup == "id":
        return User.objects.get(pk=username_or_id)
    if lookup == "username":
        return User.objects.get(username=username_or_id)

    try:
        return User.objects.get(pk=username_or_id)
    except (User.DoesNotExist, ValueError):
        return User.objects.get(username=username_or_id)


def user_not_found_response():
    return api_response(
        code=40004,
        message="用户不存在",
        data=None,
        status=status.HTTP_404_NOT_FOUND,
    )


class ProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, username_or_id):
        try:
            user = resolve_profile_user(username_or_id, request.query_params.get("lookup"))
        except (User.DoesNotExist, ValueError):
            return user_not_found_response()

        profile, _ = UserProfile.objects.get_or_create(user=user)

        if request.user.is_authenticated:
            friend_status = get_friend_status(request.user, user)
            if request.user != user:
                VisitRecord.objects.create(visitor=request.user, visited_user=user)
        else:
            friend_status = "none"

        serializer = ProfileSerializer(profile)
        data = serializer.data
        data["friend_status"] = friend_status
        return api_response(data=data)


class VisitorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username_or_id):
        try:
            user = resolve_profile_user(username_or_id, request.query_params.get("lookup"))
        except (User.DoesNotExist, ValueError):
            return user_not_found_response()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.visitor_public and request.user != user:
            return api_response(
                code=40003,
                message="无权查看访客列表",
                data=None,
                status=status.HTTP_403_FORBIDDEN,
            )

        visitors = VisitRecord.objects.filter(visited_user=user).select_related("visitor")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        total = visitors.count()
        page_visitors = visitors[start:end]

        serializer = VisitorSerializer(page_visitors, many=True)
        return api_response(
            data={
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        )


class UserPostListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, username_or_id):
        try:
            user = resolve_profile_user(username_or_id, request.query_params.get("lookup"))
        except (User.DoesNotExist, ValueError):
            return user_not_found_response()

        posts = Post.objects.filter(author=user).filter(Q(group_id__isnull=True) | Q(sync_to_profile=True)).select_related("group")

        if request.user.is_authenticated:
            friend_id_set = set()
            if request.user != user:
                is_friend = Friendship.objects.filter(
                    Q(from_user=request.user, to_user=user)
                    | Q(from_user=user, to_user=request.user),
                    status=Friendship.Status.ACCEPTED,
                ).exists()
                if is_friend:
                    friend_id_set.add(user.id)

            if request.user == user:
                pass
            elif user.id in friend_id_set:
                posts = posts.exclude(visibility=Post.Visibility.PRIVATE)
            else:
                posts = posts.filter(visibility=Post.Visibility.PUBLIC)
        else:
            posts = posts.filter(visibility=Post.Visibility.PUBLIC)

        posts = posts.order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        total = posts.count()
        page_posts = posts[start:end]

        from apps.feed.serializers import PostSerializer

        serializer = PostSerializer(
            page_posts, many=True, context={"request": request}
        )
        return api_response(
            data={
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        )


class GuestbookListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, username_or_id):
        try:
            user = resolve_profile_user(username_or_id, request.query_params.get("lookup"))
        except (User.DoesNotExist, ValueError):
            return user_not_found_response()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        entries = profile.guestbook_entries.all()

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        total = entries.count()
        page_entries = entries[start:end]

        serializer = GuestbookEntrySerializer(page_entries, many=True)
        return api_response(
            data={
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        )


class GuestbookCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, username_or_id):
        try:
            user = resolve_profile_user(username_or_id, request.query_params.get("lookup"))
        except (User.DoesNotExist, ValueError):
            return user_not_found_response()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        serializer = GuestbookCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry = GuestbookEntry.objects.create(
            profile=profile,
            author=request.user,
            content=serializer.validated_data["content"],
        )
        return api_response(
            data=GuestbookEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED,
        )


class GuestbookReplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, entry_id):
        try:
            entry = GuestbookEntry.objects.select_related(
                "profile__user"
            ).get(pk=entry_id)
        except GuestbookEntry.DoesNotExist:
            return api_response(
                code=40004,
                message="留言不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        if entry.profile.user != request.user:
            return api_response(
                code=40003,
                message="无权回复该留言",
                data=None,
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = GuestbookReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry.reply = serializer.validated_data["reply"]
        entry.replied_at = timezone.now()
        entry.save()

        return api_response(data=GuestbookEntrySerializer(entry).data)


class GuestbookDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, entry_id):
        try:
            entry = GuestbookEntry.objects.select_related(
                "profile__user"
            ).get(pk=entry_id)
        except GuestbookEntry.DoesNotExist:
            return api_response(
                code=40004,
                message="留言不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        if entry.profile.user != request.user:
            return api_response(
                code=40003,
                message="无权删除该留言",
                data=None,
                status=status.HTTP_403_FORBIDDEN,
            )

        entry.delete()
        return api_response(message="留言已删除")


class ProfileAdminView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not request.user.is_staff:
            return api_response(code=40003, message="无权访问", data=None, status=status.HTTP_403_FORBIDDEN)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return api_response(code=40004, message="用户不存在", data=None, status=status.HTTP_404_NOT_FOUND)
        return api_response(data={
            "user_id": target.id,
            "username": target.username,
            "nickname": target.nickname,
            "email": target.email,
            "is_active": target.is_active,
            "is_staff": target.is_staff,
            "is_superuser": target.is_superuser,
            "date_joined": target.date_joined,
            "last_login": target.last_login,
            "bio": target.bio,
        })

    def patch(self, request, user_id):
        if not request.user.is_staff:
            return api_response(code=40003, message="无权访问", data=None, status=status.HTTP_403_FORBIDDEN)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return api_response(code=40004, message="用户不存在", data=None, status=status.HTTP_404_NOT_FOUND)

        allowed_fields = {"is_active"}
        updated = {}
        for field in allowed_fields:
            if field in request.data:
                setattr(target, field, request.data[field])
                updated[field] = request.data[field]
        target.save(update_fields=updated.keys())

        from apps.admin_dashboard.models import SiteLog
        SiteLog.objects.create(
            user=request.user,
            action="update_user",
            detail={"target_user_id": target.id, "target_username": target.username, **updated},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return api_response(data={
            "user_id": target.id,
            "is_active": target.is_active,
        })
