from rest_framework import serializers

from .models import (
    QuizQuestionBank,
    QuizQuestionBankOption,
    QuizSubmission,
    QuizTest,
    QuizTestOption,
    QuizTestQuestion,
)


def user_brief(user):
    return {
        "user_id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar_url": user.avatar.url if getattr(user, "avatar", None) else None,
    }


class QuizOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizTestOption
        fields = ["id", "option_text", "order"]


class QuizQuestionPublicSerializer(serializers.ModelSerializer):
    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizTestQuestion
        fields = ["id", "question_type", "question_text", "order", "options"]


class QuizQuestionOwnerSerializer(serializers.ModelSerializer):
    options = QuizOptionSerializer(many=True, read_only=True)
    correct_option_id = serializers.IntegerField(read_only=True)
    source_bank_question_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuizTestQuestion
        fields = [
            "id",
            "question_type",
            "question_text",
            "order",
            "correct_option_id",
            "source_bank_question_id",
            "options",
        ]


class QuizTestCardSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    has_submitted = serializers.SerializerMethodField()

    class Meta:
        model = QuizTest
        fields = [
            "id",
            "owner",
            "title",
            "status",
            "question_count",
            "submission_count",
            "has_submitted",
            "created_at",
            "published_at",
        ]

    def get_owner(self, obj):
        return user_brief(obj.owner)

    def get_question_count(self, obj):
        return obj.questions.count()

    def get_submission_count(self, obj):
        return obj.submissions.filter(is_deleted=False).count()

    def get_has_submitted(self, obj):
        submitted_ids = self.context.get("submitted_test_ids") or set()
        return obj.id in submitted_ids


class QuizTestDetailPublicSerializer(QuizTestCardSerializer):
    questions = QuizQuestionPublicSerializer(many=True, read_only=True)
    my_submission_id = serializers.SerializerMethodField()

    class Meta:
        model = QuizTest
        fields = [
            "id",
            "owner",
            "title",
            "status",
            "question_count",
            "has_submitted",
            "my_submission_id",
            "questions",
        ]

    def get_my_submission_id(self, obj):
        submission_map = self.context.get("submission_map") or {}
        return submission_map.get(obj.id)


class QuizTestDetailOwnerSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    questions = QuizQuestionOwnerSerializer(many=True, read_only=True)

    class Meta:
        model = QuizTest
        fields = [
            "id",
            "title",
            "status",
            "question_count",
            "submission_count",
            "created_at",
            "updated_at",
            "published_at",
            "questions",
        ]

    def get_question_count(self, obj):
        return obj.questions.count()

    def get_submission_count(self, obj):
        return obj.submissions.filter(is_deleted=False).count()


class QuizSubmissionSummarySerializer(serializers.ModelSerializer):
    rank = serializers.IntegerField(read_only=True, default=None)
    is_tied = serializers.BooleanField(read_only=True, default=False)
    user = serializers.SerializerMethodField()
    total_count = serializers.IntegerField(read_only=True, default=10)
    score_percent = serializers.SerializerMethodField()
    is_current = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = QuizSubmission
        fields = [
            "id",
            "rank",
            "is_tied",
            "participant_type",
            "participant_name",
            "user",
            "correct_count",
            "total_count",
            "score_percent",
            "title",
            "is_current",
            "created_at",
        ]

    def get_user(self, obj):
        return user_brief(obj.user) if obj.user_id else None

    def get_score_percent(self, obj):
        return float(obj.score_percent)


class QuizBankOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestionBankOption
        fields = ["id", "option_text", "order"]


class QuizBankQuestionSerializer(serializers.ModelSerializer):
    options = QuizBankOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestionBank
        fields = ["id", "question_text", "tags", "options", "created_at", "updated_at"]
