from rest_framework import serializers

from apps.accounts.models import User
from apps.profiles.models import UserProfile


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "password", "nickname", "email"]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
        }

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已被注册")
        return value

    def validate_password(self, value):
        if not any(c.isalpha() for c in value):
            raise serializers.ValidationError("密码必须包含字母")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("密码必须包含数字")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for c in value):
            raise serializers.ValidationError("密码必须包含至少一个特殊字符")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    show_real_name = serializers.BooleanField(required=False)
    visitor_public = serializers.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["nickname", "bio", "email", "real_name", "show_real_name", "visitor_public"]

    def update(self, instance, validated_data):
        show_real_name = validated_data.pop("show_real_name", None)
        visitor_public = validated_data.pop("visitor_public", None)
        instance = super().update(instance, validated_data)
        if show_real_name is not None or visitor_public is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            update_fields = []
            if show_real_name is not None:
                profile.show_real_name = show_real_name
                update_fields.append("show_real_name")
            if visitor_public is not None:
                profile.visitor_public = visitor_public
                update_fields.append("visitor_public")
            profile.save(update_fields=update_fields)
        return instance


class UserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="id", read_only=True)
    avatar_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    show_real_name = serializers.SerializerMethodField()
    visitor_public = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_id",
            "username",
            "nickname",
            "real_name",
            "avatar_url",
            "cover_url",
            "bio",
            "email",
            "show_real_name",
            "visitor_public",
            "is_admin",
            "date_joined",
            "unread_count",
        ]

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None

    def get_cover_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None

    def get_show_real_name(self, obj):
        return getattr(obj, "profile", None) is not None and obj.profile.show_real_name

    def get_visitor_public(self, obj):
        return getattr(obj, "profile", None) is None or obj.profile.visitor_public

    def get_is_admin(self, obj):
        return obj.is_staff or obj.is_superuser

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated and obj.id == request.user.id:
            from apps.notifications.models import Notification
            return Notification.objects.filter(recipient=obj, is_read=False).count()
        return 0
