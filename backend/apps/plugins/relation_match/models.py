from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


BASE_QUESTION_COUNT = 40
MIN_OPTIONS_PER_QUESTION = 2
MAX_OPTIONS_PER_QUESTION = 4
DIMENSION_MIN_SCORE = 1
DIMENSION_MAX_SCORE = 10
VISITOR_COOKIE_NAME = "fmh_relation_visitor_id"
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365


class RelationMatchTest(models.Model):
    objects = models.Manager()

    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"
        DELETED = "deleted", "已删除"

    slug = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "plugins_relationmatchtest"
        app_label = "plugins"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["slug"], name="idx_rm_test_slug"),
            models.Index(fields=["status", "published_at"], name="idx_rm_test_status_pub"),
        ]

    def clean(self):
        super().clean()
        if self.status == self.Status.DELETED or not self.slug:
            return
        active_tests = RelationMatchTest.objects.exclude(status=self.Status.DELETED)
        if self.pk:
            active_tests = active_tests.exclude(pk=self.pk)
        if active_tests.exists():
            raise ValidationError({"slug": "系统只允许一套当前关系匹配测试"})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.title)


class RelationMatchQuestion(models.Model):
    objects = models.Manager()

    class Type(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "单选题"
        SCALE = "scale", "量表题"
        MULTI_SELECT = "multi_select", "多选题"
        EITHER_OR = "either_or", "二选一题"

    test = models.ForeignKey(RelationMatchTest, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=20, choices=Type.choices)
    question_text = models.CharField(max_length=120)
    scene_tag = models.CharField(max_length=50, blank=True, default="")
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plugins_relationmatchquestion"
        app_label = "plugins"
        ordering = ["order"]
        constraints = [models.UniqueConstraint(fields=["test", "order"], name="uq_relationmatch_question_order")]
        indexes = [models.Index(fields=["test", "order"], name="idx_rm_q_order")]

    def __str__(self):
        return str(self.question_text)


class RelationMatchQuestionOption(models.Model):
    objects = models.Manager()

    question = models.ForeignKey(RelationMatchQuestion, on_delete=models.CASCADE, related_name="options")
    option_text = models.CharField(max_length=60)
    order = models.PositiveIntegerField()
    dimension_payload = models.JSONField(default=dict)

    class Meta:
        db_table = "plugins_relationmatchquestionoption"
        app_label = "plugins"
        ordering = ["order"]
        constraints = [models.UniqueConstraint(fields=["question", "order"], name="uq_relationmatch_option_order")]
        indexes = [models.Index(fields=["question", "order"], name="idx_rm_qopt_order")]

    def __str__(self):
        return str(self.option_text)


class RelationMatchTestAnswer(models.Model):
    objects = models.Manager()

    class ParticipantType(models.TextChoices):
        USER = "user", "登录用户"
        VISITOR = "visitor", "未登录访客"

    test = models.ForeignKey(RelationMatchTest, on_delete=models.CASCADE, related_name="answers")
    participant_type = models.CharField(max_length=20, choices=ParticipantType.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="relation_match_answers",
    )
    participant_name = models.CharField(max_length=30)
    visitor_token_hash = models.CharField(max_length=128, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plugins_relationmatchtestanswer"
        app_label = "plugins"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["test", "user"], name="idx_rm_a_user"),
            models.Index(fields=["test", "visitor_token_hash"], name="idx_rm_a_visitor"),
            models.Index(fields=["test", "is_deleted", "created_at"], name="idx_rm_a_rank"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "user"],
                condition=Q(is_deleted=False, participant_type="user", user__isnull=False),
                name="uq_relationmatch_answer_user_active",
            ),
            models.UniqueConstraint(
                fields=["test", "visitor_token_hash"],
                condition=Q(
                    is_deleted=False,
                    participant_type="visitor",
                    visitor_token_hash__isnull=False,
                ),
                name="uq_relationmatch_answer_visitor_active",
            ),
        ]

    def __str__(self):
        return f"{self.participant_name} - {self.test.pk}"


class RelationMatchTestAnswerItem(models.Model):
    objects = models.Manager()

    answer = models.ForeignKey(RelationMatchTestAnswer, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(RelationMatchQuestion, on_delete=models.CASCADE, related_name="answer_items")
    selected_options = models.JSONField()
    dimension_payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plugins_relationmatchtestansweritem"
        app_label = "plugins"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["answer", "question"], name="uq_relationmatch_answer_item_question")]


class RelationMatchProfile(models.Model):
    objects = models.Manager()

    class ParticipantType(models.TextChoices):
        USER = "user", "登录用户"
        VISITOR = "visitor", "未登录访客"

    participant_type = models.CharField(max_length=20, choices=ParticipantType.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="relation_match_profiles",
    )
    participant_name = models.CharField(max_length=30)
    visitor_token_hash = models.CharField(max_length=128, null=True, blank=True)
    test = models.ForeignKey(RelationMatchTest, on_delete=models.CASCADE, related_name="profiles")
    dimension_scores = models.JSONField()
    summary_text = models.TextField()
    share_code = models.CharField(max_length=20, unique=True)
    share_token = models.CharField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plugins_relationmatchprofile"
        app_label = "plugins"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["participant_type", "user"], name="idx_rm_p_user"),
            models.Index(fields=["visitor_token_hash"], name="idx_rm_p_visitor"),
            models.Index(fields=["share_code"], name="idx_rm_p_share_code"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=Q(participant_type="user", user__isnull=False), name="uq_relationmatch_profile_user"),
            models.UniqueConstraint(fields=["visitor_token_hash"], condition=Q(participant_type="visitor", visitor_token_hash__isnull=False), name="uq_relationmatch_profile_visitor"),
        ]

    def __str__(self):
        return str(self.participant_name)


class RelationMatchPairResult(models.Model):
    objects = models.Manager()

    profile_a = models.ForeignKey(RelationMatchProfile, on_delete=models.CASCADE, related_name="pair_results_as_a")
    profile_b = models.ForeignKey(RelationMatchProfile, on_delete=models.CASCADE, related_name="pair_results_as_b")
    relation_type = models.CharField(max_length=50)
    subtitle = models.CharField(max_length=80)
    summary_a = models.TextField()
    summary_b = models.TextField()
    role_a = models.CharField(max_length=50)
    role_b = models.CharField(max_length=50)
    dimension_compare = models.JSONField()
    relation_explain = models.TextField()
    highlight_text = models.TextField()
    advice_text = models.TextField()
    share_token = models.CharField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plugins_relationmatchpairresult"
        app_label = "plugins"
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["profile_a", "profile_b"], name="uq_relationmatch_pair_unique")]
        indexes = [models.Index(fields=["created_at"], name="idx_rm_pair_created")]

    def __str__(self):
        return f"{self.profile_a.pk}-{self.profile_b.pk}"


class RelationMatchPairResultMember(models.Model):
    objects = models.Manager()

    result = models.ForeignKey(RelationMatchPairResult, on_delete=models.CASCADE, related_name="members")
    profile = models.ForeignKey(RelationMatchProfile, on_delete=models.CASCADE, related_name="result_memberships")
    access_token_hash = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plugins_relationmatchpairresultmember"
        app_label = "plugins"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["result", "profile"], name="uq_relationmatch_pair_member")]
