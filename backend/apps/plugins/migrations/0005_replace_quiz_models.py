# Generated manually for the quiz Phase 1 model rewrite.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plugins", "0004_rename_type_plugin_plugin_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(
            name="QuizAnswer",
        ),
        migrations.DeleteModel(
            name="QuizResult",
        ),
        migrations.DeleteModel(
            name="QuizQuestion",
        ),
        migrations.CreateModel(
            name="QuizTest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=30)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "草稿"), ("published", "已发布"), ("deleted", "已删除")],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_tests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "plugins_quiztest",
                "indexes": [
                    models.Index(fields=["owner", "status"], name="idx_quiztest_owner_status"),
                    models.Index(fields=["status", "published_at"], name="idx_quiztest_status_published"),
                ],
            },
        ),
        migrations.CreateModel(
            name="QuizQuestionBank",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_text", models.CharField(max_length=80)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "plugins_quizquestionbank",
            },
        ),
        migrations.CreateModel(
            name="QuizTestQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "question_type",
                    models.CharField(choices=[("single_choice", "单选题")], default="single_choice", max_length=20),
                ),
                ("question_text", models.CharField(max_length=80)),
                ("order", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "source_bank_question",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="copied_test_questions",
                        to="plugins.quizquestionbank",
                    ),
                ),
                (
                    "test",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="plugins.quiztest",
                    ),
                ),
            ],
            options={
                "db_table": "plugins_quiztestquestion",
                "indexes": [models.Index(fields=["test", "order"], name="idx_quiztestquestion_order")],
                "constraints": [
                    models.UniqueConstraint(fields=("test", "order"), name="uq_quiz_test_question_order"),
                ],
            },
        ),
        migrations.CreateModel(
            name="QuizTestOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("option_text", models.CharField(max_length=30)),
                ("order", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="plugins.quiztestquestion",
                    ),
                ),
            ],
            options={
                "db_table": "plugins_quiztestoption",
                "indexes": [models.Index(fields=["question", "order"], name="idx_quiztestoption_order")],
                "constraints": [
                    models.UniqueConstraint(fields=("question", "order"), name="uq_quiz_test_option_order"),
                ],
            },
        ),
        migrations.AddField(
            model_name="quiztestquestion",
            name="correct_option",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="correct_for_questions",
                to="plugins.quiztestoption",
            ),
        ),
        migrations.CreateModel(
            name="QuizSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "participant_type",
                    models.CharField(choices=[("user", "登录用户"), ("visitor", "未登录访客")], max_length=20),
                ),
                ("participant_name", models.CharField(max_length=30)),
                ("visitor_token_hash", models.CharField(blank=True, max_length=128, null=True)),
                ("correct_count", models.PositiveIntegerField()),
                ("score_percent", models.DecimalField(decimal_places=2, max_digits=5)),
                ("title", models.CharField(max_length=50)),
                ("is_deleted", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "test",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="plugins.quiztest",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "plugins_quizsubmission",
                "indexes": [
                    models.Index(
                        fields=["test", "is_deleted", "score_percent", "correct_count", "created_at"],
                        name="idx_quizsubmission_rank",
                    ),
                    models.Index(fields=["test", "user"], name="idx_quizsubmission_user"),
                    models.Index(fields=["test", "visitor_token_hash"], name="idx_quizsubmission_visitor"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_deleted", False), ("participant_type", "user"), ("user__isnull", False)),
                        fields=("test", "user"),
                        name="uq_quiz_submission_user_active",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(
                            ("is_deleted", False),
                            ("participant_type", "visitor"),
                            ("visitor_token_hash__isnull", False),
                        ),
                        fields=("test", "visitor_token_hash"),
                        name="uq_quiz_submission_visitor_active",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("correct_count__lte", 10)),
                        name="ck_quiz_submission_correct_count_lte_10",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("score_percent__gte", 0), ("score_percent__lte", 100)),
                        name="ck_quiz_submission_score_percent_range",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="QuizSubmissionAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_correct", models.BooleanField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submission_answers",
                        to="plugins.quiztestquestion",
                    ),
                ),
                (
                    "selected_option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submission_answers",
                        to="plugins.quiztestoption",
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="plugins.quizsubmission",
                    ),
                ),
            ],
            options={
                "db_table": "plugins_quizsubmissionanswer",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("submission", "question"),
                        name="uq_quiz_submission_answer_question",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="QuizQuestionBankOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("option_text", models.CharField(max_length=30)),
                ("order", models.PositiveIntegerField()),
                (
                    "bank_question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="plugins.quizquestionbank",
                    ),
                ),
            ],
            options={
                "db_table": "plugins_quizquestionbankoption",
                "indexes": [models.Index(fields=["bank_question", "order"], name="idx_quizbankoption_order")],
                "constraints": [
                    models.UniqueConstraint(fields=("bank_question", "order"), name="uq_quiz_bank_option_order"),
                ],
            },
        ),
    ]
