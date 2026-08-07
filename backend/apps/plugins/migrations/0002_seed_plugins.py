from django.db import migrations


def seed_plugins(apps, schema_editor):
    Plugin = apps.get_model("plugins", "Plugin")
    Plugin.objects.get_or_create(
        type="quiz",
        defaults={"name": "默契问答", "is_active": True},
    )
    Plugin.objects.get_or_create(
        type="question_box",
        defaults={"name": "匿名提问箱", "is_active": True},
    )
    Plugin.objects.get_or_create(
        type="relation_match",
        defaults={"name": "关系匹配", "is_active": True},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("plugins", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed_plugins),
    ]
