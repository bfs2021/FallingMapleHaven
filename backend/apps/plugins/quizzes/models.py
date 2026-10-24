from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


MAX_TESTS_PER_OWNER = 3
PUBLISHED_QUESTION_COUNT = 10
MIN_OPTIONS_PER_QUESTION = 2
MAX_OPTIONS_PER_QUESTION = 4


class QuizTest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"
        DELETED = "deleted", "已删除"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_tests",
    )
    title = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "plugins_quiztest"
        indexes = [
            models.Index(fields=["owner", "status"], name="idx_quiztest_owner_status"),
            models.Index(fields=["status", "published_at"], name="idx_quiztest_status_published"),
        ]

    def clean(self):
        super().clean()
        if self.status == self.Status.DELETED or not self.owner_id:
            return

        active_tests = QuizTest.objects.filter(owner_id=self.owner_id).exclude(
            status=self.Status.DELETED
        )
        if self.pk:
            active_tests = active_tests.exclude(pk=self.pk)
        if active_tests.count() >= MAX_TESTS_PER_OWNER:
            raise ValidationError({"owner": "同一主页主人最多创建 3 套未删除测试"})

    def __str__(self):
        return self.title


class QuizQuestionBank(models.Model):
    question_text = models.CharField(max_length=80)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plugins_quizquestionbank"

    def __str__(self):
        return self.question_text


class QuizTestQuestion(models.Model):
    class Type(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "单选题"

    test = models.ForeignKey(
        QuizTest,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SINGLE_CHOICE,
    )
    question_text = models.CharField(max_length=80)
    order = models.PositiveIntegerField()
    correct_option = models.ForeignKey(
        "QuizTestOption",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correct_for_questions",
    )
    source_bank_question = models.ForeignKey(
        QuizQuestionBank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="copied_test_questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plugins_quiztestquestion"
        indexes = [models.Index(fields=["test", "order"], name="idx_quiztestquestion_order")]
        constraints = [
            models.UniqueConstraint(fields=["test", "order"], name="uq_quiz_test_question_order"),
        ]

    def __str__(self):
        return self.question_text


class QuizTestOption(models.Model):
    question = models.ForeignKey(
        QuizTestQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.CharField(max_length=30)
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plugins_quiztestoption"
        indexes = [models.Index(fields=["question", "order"], name="idx_quiztestoption_order")]
        constraints = [
            models.UniqueConstraint(fields=["question", "order"], name="uq_quiz_test_option_order"),
        ]

    def __str__(self):
        return self.option_text


class QuizSubmission(models.Model):
    class ParticipantType(models.TextChoices):
        USER = "user", "登录用户"
        VISITOR = "visitor", "未登录访客"

    test = models.ForeignKey(
        QuizTest,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    participant_type = models.CharField(max_length=20, choices=ParticipantType.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="quiz_submissions",
    )
    participant_name = models.CharField(max_length=30)
    visitor_token_hash = models.CharField(max_length=128, null=True, blank=True)
    correct_count = models.PositiveIntegerField()
    score_percent = models.DecimalField(max_digits=5, decimal_places=2)
    title = models.CharField(max_length=50)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plugins_quizsubmission"
        indexes = [
            models.Index(
                fields=["test", "is_deleted", "score_percent", "correct_count", "created_at"],
                name="idx_quizsubmission_rank",
            ),
            models.Index(fields=["test", "user"], name="idx_quizsubmission_user"),
            models.Index(fields=["test", "visitor_token_hash"], name="idx_quizsubmission_visitor"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "user"],
                condition=Q(is_deleted=False, participant_type="user", user__isnull=False),
                name="uq_quiz_submission_user_active",
            ),
            models.UniqueConstraint(
                fields=["test", "visitor_token_hash"],
                condition=Q(
                    is_deleted=False,
                    participant_type="visitor",
                    visitor_token_hash__isnull=False,
                ),
                name="uq_quiz_submission_visitor_active",
            ),
            models.CheckConstraint(
                condition=Q(correct_count__lte=PUBLISHED_QUESTION_COUNT),
                name="ck_quiz_submission_correct_count_lte_10",
            ),
            models.CheckConstraint(
                condition=Q(score_percent__gte=0) & Q(score_percent__lte=100),
                name="ck_quiz_submission_score_percent_range",
            ),
        ]

    def __str__(self):
        return f"{self.participant_name} - {self.test_id}"


class QuizSubmissionAnswer(models.Model):
    submission = models.ForeignKey(
        QuizSubmission,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        QuizTestQuestion,
        on_delete=models.CASCADE,
        related_name="submission_answers",
    )
    selected_option = models.ForeignKey(
        QuizTestOption,
        on_delete=models.CASCADE,
        related_name="submission_answers",
    )
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plugins_quizsubmissionanswer"
        constraints = [
            models.UniqueConstraint(fields=["submission", "question"], name="uq_quiz_submission_answer_question"),
        ]

    def __str__(self):
        return f"{self.submission_id} - {self.question_id}"


class QuizQuestionBankOption(models.Model):
    bank_question = models.ForeignKey(
        QuizQuestionBank,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.CharField(max_length=30)
    order = models.PositiveIntegerField()

    class Meta:
        db_table = "plugins_quizquestionbankoption"
        indexes = [models.Index(fields=["bank_question", "order"], name="idx_quizbankoption_order")]
        constraints = [
            models.UniqueConstraint(fields=["bank_question", "order"], name="uq_quiz_bank_option_order"),
        ]

    def __str__(self):
        return self.option_text
