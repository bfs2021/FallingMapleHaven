from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User
from .catalog import RELATION_TYPES
from .models import (
    RelationMatchPairResult,
    RelationMatchProfile,
    RelationMatchQuestion,
    RelationMatchQuestionOption,
    RelationMatchTest,
)


def user_brief(user: User | None):
    if user is None:
        return None
    return {
        "user_id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar_url": user.avatar.url if getattr(user, "avatar", None) else None,
    }


class RelationMatchOptionPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationMatchQuestionOption
        fields = ["id", "option_text", "order"]


class RelationMatchQuestionPublicSerializer(serializers.ModelSerializer):
    options = RelationMatchOptionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = RelationMatchQuestion
        fields = ["id", "question_type", "question_text", "scene_tag", "order", "options"]


class RelationMatchProfileSummarySerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = RelationMatchProfile
        fields = [
            "id",
            "participant_type",
            "participant_name",
            "user",
            "dimension_scores",
            "summary_text",
            "share_code",
            "share_url",
        ]

    def get_user(self, obj):
        return user_brief(obj.user)

    def get_share_url(self, obj):
        return f"/profile/{obj.user_id or obj.id}/plugins/relation-match?shareCode={obj.share_code}"


class RelationMatchPairResultDetailSerializer(serializers.ModelSerializer):
    relation_type_name = serializers.SerializerMethodField()
    profile_a = RelationMatchProfileSummarySerializer(read_only=True)
    profile_b = RelationMatchProfileSummarySerializer(read_only=True)
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = RelationMatchPairResult
        fields = [
            "id",
            "relation_type",
            "relation_type_name",
            "subtitle",
            "profile_a",
            "profile_b",
            "summary_a",
            "summary_b",
            "role_a",
            "role_b",
            "dimension_compare",
            "relation_explain",
            "highlight_text",
            "advice_text",
            "share_url",
        ]

    def get_relation_type_name(self, obj):
        return RELATION_TYPES[obj.relation_type]["name"]

    def get_share_url(self, obj):
        return f"/profile/{obj.profile_a.user_id or obj.profile_a.id}/plugins/relation-match/pairs/{obj.id}/"


class RelationMatchHistoryItemSerializer(serializers.Serializer):
    pair_id = serializers.IntegerField()
    relation_type_name = serializers.CharField()
    subtitle = serializers.CharField()
    other_participant_name = serializers.CharField()
    result_url = serializers.CharField()
    created_at = serializers.DateTimeField()


class RelationMatchHomeProfileSerializer(serializers.ModelSerializer):
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = RelationMatchProfile
        fields = ["id", "participant_name", "share_code", "share_url"]

    def get_share_url(self, obj):
        return f"/profile/{obj.user_id or obj.id}/plugins/relation-match?shareCode={obj.share_code}"


class RelationMatchCurrentTestSerializer(serializers.ModelSerializer):
    questions = RelationMatchQuestionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = RelationMatchTest
        fields = ["id", "title", "questions"]


class RelationMatchSubmissionResponseSerializer(serializers.Serializer):
    profile = RelationMatchProfileSummarySerializer()
    next_action = serializers.CharField()
    share_code = serializers.CharField()
    share_url = serializers.CharField()
    pair = RelationMatchPairResultDetailSerializer(allow_null=True)
