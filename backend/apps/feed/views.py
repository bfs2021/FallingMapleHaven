import os

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.feed.models import Comment, Like, Post, PostFile, PostImage
from apps.friends.models import Friendship
from apps.feed.serializers import (
    CommentCreateSerializer,
    CommentSerializer,
    PostCreateSerializer,
    PostSerializer,
)

from apps.common.utils import api_response, safe_int

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".zip", ".txt", ".md", ".csv", ".xlsx", ".pptx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class PostListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            user = request.user
            friend_ids = Friendship.objects.filter(
                Q(from_user=user) | Q(to_user=user),
                status=Friendship.Status.ACCEPTED,
            ).values_list("from_user_id", "to_user_id")
            friend_id_set = set()
            for from_id, to_id in friend_ids:
                friend_id_set.add(from_id)
                friend_id_set.add(to_id)
            friend_id_set.discard(user.id)

            posts = Post.objects.filter(
                Q(visibility=Post.Visibility.PUBLIC)
                | Q(visibility=Post.Visibility.FRIENDS, author_id__in=friend_id_set)
                | Q(author=user)
            ).filter(group_id__isnull=True)
        else:
            posts = Post.objects.filter(visibility=Post.Visibility.PUBLIC, group_id__isnull=True)

        topic = request.query_params.get("topic", "").strip()
        if topic:
            posts = posts.filter(topic_tag=topic)

        posts = posts.order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        total = posts.count()
        page_posts = posts[start:end].select_related("author").prefetch_related("images", "comments", "likes")

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


class PostCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content = serializer.validated_data["content"]
        visibility = serializer.validated_data["visibility"]
        topic_tag = serializer.validated_data.get("topic_tag", "")
        image_files = serializer.validated_data.get("images", [])
        file_files = serializer.validated_data.get("files", [])

        if len(image_files) > 9:
            return api_response(
                code=40001,
                message="图片最多上传9张",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )

        for img in image_files:
            ext = os.path.splitext(img.name)[1].lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                return api_response(
                    code=40001,
                    message=f"图片格式不支持: {img.name}",
                    data=None,
                    status=status.HTTP_400_BAD_REQUEST,
                )

        for f in file_files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_FILE_EXTENSIONS:
                return api_response(code=40001, message=f"文件类型不支持: {f.name}", data=None, status=status.HTTP_400_BAD_REQUEST)
            if f.size > MAX_FILE_SIZE:
                return api_response(code=40001, message=f"文件过大(最大50MB): {f.name}", data=None, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            post = Post.objects.create(
                author=request.user,
                content=content,
                visibility=visibility,
                topic_tag=topic_tag,
                group_id=serializer.validated_data.get("group_id"),
                sync_to_profile=serializer.validated_data.get("sync_to_profile", False),
            )

            for idx, img in enumerate(image_files):
                PostImage.objects.create(post=post, image=img, order=idx)

            for idx, f in enumerate(file_files):
                PostFile.objects.create(
                    post=post,
                    file=f,
                    name=f.name,
                    size=f.size,
                    order=idx,
                )

        if post.group_id:
            from apps.groups.models import GroupMember
            from apps.notifications.models import Notification
            members = GroupMember.objects.filter(group_id=post.group_id).exclude(user=request.user).select_related("user")
            for m in members:
                Notification.objects.create(
                    recipient=m.user,
                    sender=request.user,
                    type="group_new_post",
                    title="小组新动态",
                    content=f"{request.user.nickname} 在 {post.group.name} 发布了新动态",
                    link="",
                )

        return api_response(
            data=PostSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class PostDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return api_response(
                code=40004,
                message="动态不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        if post.visibility != Post.Visibility.PUBLIC and not request.user.is_authenticated:
            return api_response(
                code=40003,
                message="无权查看该动态",
                data=None,
                status=status.HTTP_403_FORBIDDEN,
            )

        if post.visibility == Post.Visibility.PRIVATE and post.author != request.user:
            return api_response(
                code=40003,
                message="无权查看该动态",
                data=None,
                status=status.HTTP_403_FORBIDDEN,
            )

        if post.visibility == Post.Visibility.FRIENDS and post.author != request.user:
            is_friend = Friendship.objects.filter(
                Q(from_user=request.user, to_user=post.author)
                | Q(from_user=post.author, to_user=request.user),
                status=Friendship.Status.ACCEPTED,
            ).exists()
            if not is_friend:
                return api_response(
                    code=40003,
                    message="无权查看该动态",
                    data=None,
                    status=status.HTTP_403_FORBIDDEN,
                )

        return api_response(
            data=PostSerializer(post, context={"request": request}).data
        )


class PostDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return api_response(
                code=40004,
                message="动态不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        if post.author != request.user and not request.user.is_staff:
            return api_response(
                code=40003,
                message="仅作者可删除",
                data=None,
                status=status.HTTP_403_FORBIDDEN,
            )

        post.delete()
        return api_response(message="动态已删除")


class LikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return api_response(
                code=40004,
                message="动态不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            like, created = Like.objects.get_or_create(post=post, user=request.user)
            if not created:
                like.delete()
                is_liked = False
            else:
                is_liked = True

        return api_response(
            data={"is_liked": is_liked, "like_count": post.likes.count()}
        )


class CommentListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return api_response(
                code=40004,
                message="动态不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        comments = post.comments.filter(parent__isnull=True)
        serializer = CommentSerializer(comments, many=True)
        return api_response(data=serializer.data)


class CommentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return api_response(
                code=40004,
                message="动态不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parent_id = serializer.validated_data.get("parent")
        if parent_id:
            try:
                parent = Comment.objects.get(pk=parent_id, post=post)
            except Comment.DoesNotExist:
                return api_response(
                    code=40004,
                    message="父评论不存在",
                    data=None,
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            parent = None

        comment = Comment.objects.create(
            post=post,
            author=request.user,
            content=serializer.validated_data["content"],
            parent=parent,
        )

        return api_response(
            data=CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )


class CommentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            return api_response(
                code=40004,
                message="评论不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )

        if comment.author != request.user and comment.post.author != request.user and not request.user.is_staff:
            return api_response(
                code=40003,
                message="无权删除该评论",
                data=None,
                status=status.HTTP_403_FORBIDDEN,
            )

        comment.delete()
        return api_response(message="评论已删除")
