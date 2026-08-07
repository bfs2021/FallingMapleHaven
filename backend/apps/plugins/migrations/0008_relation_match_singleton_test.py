from django.db import migrations


TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION relation_match_single_active_test()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('relation_match_single_active_test'));
    IF NEW.status <> 'deleted' AND EXISTS (
        SELECT 1
        FROM plugins_relationmatchtest
        WHERE status <> 'deleted' AND id <> NEW.id
    ) THEN
        RAISE EXCEPTION 'only one active relation match test is allowed';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_TRIGGER = """
CREATE TRIGGER relation_match_single_active_test_trigger
BEFORE INSERT OR UPDATE OF status ON plugins_relationmatchtest
FOR EACH ROW EXECUTE FUNCTION relation_match_single_active_test();
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS relation_match_single_active_test_trigger
ON plugins_relationmatchtest;
DROP FUNCTION IF EXISTS relation_match_single_active_test();
"""


def install_postgres_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(TRIGGER_FUNCTION)
    schema_editor.execute(CREATE_TRIGGER)


def uninstall_postgres_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(DROP_TRIGGER)


class Migration(migrations.Migration):
    dependencies = [
        ("plugins", "0007_seed_relation_match_current"),
    ]

    operations = [
        migrations.RunPython(install_postgres_trigger, uninstall_postgres_trigger),
    ]
