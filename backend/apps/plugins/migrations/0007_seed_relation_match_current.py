from django.db import migrations

from apps.plugins.relation_match.catalog import build_current_test_seed


def seed_current_test(apps, schema_editor):
    RelationMatchTest = apps.get_model("plugins", "RelationMatchTest")
    RelationMatchQuestion = apps.get_model("plugins", "RelationMatchQuestion")
    RelationMatchQuestionOption = apps.get_model("plugins", "RelationMatchQuestionOption")

    test, _ = RelationMatchTest.objects.get_or_create(
        slug="current",
        defaults={"title": "关系匹配基础测试", "status": "published"},
    )
    if RelationMatchQuestion.objects.filter(test=test).count() == 40:
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
        ("plugins", "0006_relation_match_initial"),
    ]

    operations = [migrations.RunPython(seed_current_test, migrations.RunPython.noop)]
