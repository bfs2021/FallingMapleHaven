from django.db import migrations

from apps.plugins.relation_match.catalog import build_current_test_seed


def replace_question_bank(apps, schema_editor):
    """用 Docs/18 定稿题库替换 0007 写入的占位题（Docs/18 §7.3 开发期种子重置）。"""
    RelationMatchTest = apps.get_model("plugins", "RelationMatchTest")
    RelationMatchQuestion = apps.get_model("plugins", "RelationMatchQuestion")
    RelationMatchQuestionOption = apps.get_model("plugins", "RelationMatchQuestionOption")

    test = RelationMatchTest.objects.filter(slug="current").first()
    if test is None:
        return
    RelationMatchQuestion.objects.filter(test=test).delete()
    for order, seed in enumerate(build_current_test_seed(), 1):
        question = RelationMatchQuestion.objects.create(
            test=test,
            question_type=seed.question_type,
            question_text=seed.question_text,
            scene_tag=seed.scene_tag,
            order=order,
        )
        for option_order, (option_text, payload) in enumerate(zip(seed.option_texts, seed.option_payloads), 1):
            RelationMatchQuestionOption.objects.create(
                question=question,
                option_text=option_text,
                order=option_order,
                dimension_payload=payload,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("plugins", "0009_seed_relation_match_plugin"),
    ]

    operations = [migrations.RunPython(replace_question_bank, migrations.RunPython.noop)]
