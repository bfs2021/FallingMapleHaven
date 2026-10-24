from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("plugins", "0005_replace_quiz_models"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RelationMatchTest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.CharField(max_length=50, unique=True)),
                ("title", models.CharField(max_length=50)),
                ("status", models.CharField(choices=[("draft", "草稿"), ("published", "已发布"), ("deleted", "已删除")], default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "plugins_relationmatchtest",
                "indexes": [
                    models.Index(fields=["slug"], name="idx_rm_test_slug"),
                    models.Index(fields=["status", "published_at"], name="idx_rm_test_status_pub"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RelationMatchQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_type", models.CharField(choices=[("single_choice", "单选题"), ("scale", "量表题"), ("multi_select", "多选题"), ("either_or", "二选一题")], max_length=20)),
                ("question_text", models.CharField(max_length=120)),
                ("scene_tag", models.CharField(blank=True, default="", max_length=50)),
                ("order", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("test", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="plugins.relationmatchtest")),
            ],
            options={
                "db_table": "plugins_relationmatchquestion",
                "indexes": [models.Index(fields=["test", "order"], name="idx_rm_q_order")],
                "constraints": [models.UniqueConstraint(fields=("test", "order"), name="uq_relationmatch_question_order")],
            },
        ),
        migrations.CreateModel(
            name="RelationMatchQuestionOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("option_text", models.CharField(max_length=60)),
                ("order", models.PositiveIntegerField()),
                ("dimension_payload", models.JSONField(default=dict)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="plugins.relationmatchquestion")),
            ],
            options={
                "db_table": "plugins_relationmatchquestionoption",
                "indexes": [models.Index(fields=["question", "order"], name="idx_rm_qopt_order")],
                "constraints": [models.UniqueConstraint(fields=("question", "order"), name="uq_relationmatch_option_order")],
            },
        ),
        migrations.CreateModel(
            name="RelationMatchTestAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("participant_type", models.CharField(choices=[("user", "登录用户"), ("visitor", "未登录访客")], max_length=20)),
                ("participant_name", models.CharField(max_length=30)),
                ("visitor_token_hash", models.CharField(blank=True, max_length=128, null=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("test", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="plugins.relationmatchtest")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="relation_match_answers", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "plugins_relationmatchtestanswer",
                "indexes": [
                    models.Index(fields=["test", "user"], name="idx_rm_a_user"),
                    models.Index(fields=["test", "visitor_token_hash"], name="idx_rm_a_visitor"),
                    models.Index(fields=["test", "is_deleted", "created_at"], name="idx_rm_a_rank"),
                ],
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("is_deleted", False), ("participant_type", "user"), ("user__isnull", False)), fields=("test", "user"), name="uq_relationmatch_answer_user_active"),
                    models.UniqueConstraint(condition=models.Q(("is_deleted", False), ("participant_type", "visitor"), ("visitor_token_hash__isnull", False)), fields=("test", "visitor_token_hash"), name="uq_relationmatch_answer_visitor_active"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RelationMatchProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("participant_type", models.CharField(choices=[("user", "登录用户"), ("visitor", "未登录访客")], max_length=20)),
                ("participant_name", models.CharField(max_length=30)),
                ("visitor_token_hash", models.CharField(blank=True, max_length=128, null=True)),
                ("dimension_scores", models.JSONField()),
                ("summary_text", models.TextField()),
                ("share_code", models.CharField(max_length=20, unique=True)),
                ("share_token", models.CharField(max_length=80, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("test", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profiles", to="plugins.relationmatchtest")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="relation_match_profiles", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "plugins_relationmatchprofile",
                "indexes": [
                    models.Index(fields=["participant_type", "user"], name="idx_rm_p_user"),
                    models.Index(fields=["visitor_token_hash"], name="idx_rm_p_visitor"),
                    models.Index(fields=["share_code"], name="idx_rm_p_share_code"),
                ],
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("participant_type", "user"), ("user__isnull", False)), fields=("user",), name="uq_relationmatch_profile_user"),
                    models.UniqueConstraint(condition=models.Q(("participant_type", "visitor"), ("visitor_token_hash__isnull", False)), fields=("visitor_token_hash",), name="uq_relationmatch_profile_visitor"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RelationMatchPairResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("relation_type", models.CharField(max_length=50)),
                ("subtitle", models.CharField(max_length=80)),
                ("summary_a", models.TextField()),
                ("summary_b", models.TextField()),
                ("role_a", models.CharField(max_length=50)),
                ("role_b", models.CharField(max_length=50)),
                ("dimension_compare", models.JSONField()),
                ("relation_explain", models.TextField()),
                ("highlight_text", models.TextField()),
                ("advice_text", models.TextField()),
                ("share_token", models.CharField(max_length=80, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("profile_a", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pair_results_as_a", to="plugins.relationmatchprofile")),
                ("profile_b", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pair_results_as_b", to="plugins.relationmatchprofile")),
            ],
            options={
                "db_table": "plugins_relationmatchpairresult",
                "indexes": [models.Index(fields=["created_at"], name="idx_rm_pair_created")],
                "constraints": [models.UniqueConstraint(fields=("profile_a", "profile_b"), name="uq_relationmatch_pair_unique")],
            },
        ),
        migrations.CreateModel(
            name="RelationMatchTestAnswerItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("selected_options", models.JSONField()),
                ("dimension_payload", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("answer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="plugins.relationmatchtestanswer")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answer_items", to="plugins.relationmatchquestion")),
            ],
            options={
                "db_table": "plugins_relationmatchtestansweritem",
                "constraints": [models.UniqueConstraint(fields=("answer", "question"), name="uq_relationmatch_answer_item_question")],
            },
        ),
        migrations.CreateModel(
            name="RelationMatchPairResultMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("access_token_hash", models.CharField(blank=True, max_length=128, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="result_memberships", to="plugins.relationmatchprofile")),
                ("result", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="plugins.relationmatchpairresult")),
            ],
            options={
                "db_table": "plugins_relationmatchpairresultmember",
                "constraints": [models.UniqueConstraint(fields=("result", "profile"), name="uq_relationmatch_pair_member")],
            },
        ),
    ]
