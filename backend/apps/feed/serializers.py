from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.feed.models import Comment, Like, Post, PostFile, PostImage


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ["id", "image", "order"]


class PostFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostFile
        fields = ["id", "file", "name", "size", "order"]


class PostSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    images = PostImageSerializer(many=True, read_only=True)
    image_urls = serializers.SerializerMethodField()
    files = PostFileSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "user",
            "content",
            "visibility",
            "topic_tag",
            "group_id",
            "group",
            "sync_to_profile",
            "images",
            "image_urls",
            "files",
            "comment_count",
            "like_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]

    def get_user(self, obj):
        return UserSerializer(obj.author, context=self.context).data

    def get_image_urls(self, obj):
        return [img.image.url for img in obj.images.all()]

    def get_comment_count(self, obj):
        return len(obj.comments.all())

    def get_like_count(self, obj):
        return len(obj.likes.all())

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()

    def get_group(self, obj):
        if obj.group_id:
            return {"id": obj.group_id, "name": obj.group.name}
        return None


class PostCreateSerializer(serializers.Serializer):
    content = serializers.CharField(required=True, max_length=2000)
    visibility = serializers.ChoiceField(
        choices=Post.Visibility.choices, default=Post.Visibility.PUBLIC
    )
    topic_tag = serializers.CharField(required=False, allow_blank=True, default="")
    group_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    sync_to_profile = serializers.BooleanField(required=False, default=False)
    images = serializers.ListField(
        child=serializers.FileField(), required=False, default=list
    )
    files = serializers.ListField(
        child=serializers.FileField(), required=False, default=list
    )


class CommentAuthorSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "nickname", "avatar", "avatar_url"]

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "user", "content", "parent", "created_at"]

    def get_user(self, obj):
        return CommentAuthorSerializer(obj.author, context=self.context).data


class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(required=True)
    parent = serializers.IntegerField(required=False, allow_null=True)
