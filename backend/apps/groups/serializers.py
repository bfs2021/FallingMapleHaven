from rest_framework import serializers
from apps.chat.models import ChatRoom
from apps.groups.models import GroupJoinRequest, GroupMember, InterestGroup


class GroupMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id")
    nickname = serializers.CharField(source="user.nickname")
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = GroupMember
        fields = ["user_id", "nickname", "avatar_url", "role", "joined_at"]

    def get_avatar_url(self, obj):
        return obj.user.avatar.url if obj.user.avatar else None


class GroupListSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    is_member = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = InterestGroup
        fields = ["id", "name", "description", "cover_url", "is_public", "member_count", "is_member", "created_at"]

    def get_is_member(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.members.filter(user_id=request.user.id).exists()
        return False

    def get_cover_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None


class GroupDetailSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    members = GroupMemberSerializer(many=True)
    cover_url = serializers.SerializerMethodField()
    chat_room_id = serializers.SerializerMethodField()

    class Meta:
        model = InterestGroup
        fields = ["id", "name", "description", "cover_url", "is_public", "owner", "member_count", "is_member", "members", "created_at", "updated_at", "chat_room_id"]

    def get_member_count(self, obj):
        return getattr(obj, 'member_count', None) or obj.members.count()

    def get_is_member(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.members.filter(user_id=request.user.id).exists()
        return False

    def get_owner(self, obj):
        return {"user_id": obj.creator.id, "nickname": obj.creator.nickname}

    def get_cover_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None

    def get_chat_room_id(self, obj):
        room = getattr(obj, '_chat_room', None)
        if room is None:
            room = ChatRoom.objects.filter(group=obj).first()
        return room.id if room else None


class GroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = ["name", "description", "cover_image", "is_public"]


class GroupUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = ["name", "description", "cover_image", "is_public"]


class GroupJoinRequestSerializer(serializers.ModelSerializer):
    applicant = serializers.SerializerMethodField()

    class Meta:
        model = GroupJoinRequest
        fields = ["id", "applicant", "status", "created_at"]

    def get_applicant(self, obj):
        return {
            "user_id": obj.applicant.id,
            "nickname": obj.applicant.nickname,
            "avatar_url": obj.applicant.avatar.url if obj.applicant.avatar else None,
        }
