from django.db import migrations


def seed_relation_match_plugin(apps, schema_editor):
    # 0002_seed_plugins.py 在历史库上应用时并未包含 relation_match，
    # 修改已应用的迁移不会重跑，故在此补写启用记录。
    Plugin = apps.get_model("plugins", "Plugin")
    Plugin.objects.get_or_create(
        plugin_type="relation_match",
        defaults={"name": "关系匹配", "is_active": True},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("plugins", "0008_relation_match_singleton_test"),
    ]
    operations = [
        migrations.RunPython(seed_relation_match_plugin),
    ]