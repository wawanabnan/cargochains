from django.db import migrations

def ensure_uom_id(apps, schema_editor):
    table = "job_costs"

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = 'uom_id'
            """,
            [table],
        )
        exists = cursor.fetchone()[0] > 0

    if not exists:
        schema_editor.execute(f"ALTER TABLE {table} ADD COLUMN uom_id BIGINT NOT NULL")

class Migration(migrations.Migration):
    atomic = False  # penting untuk MySQL DDL

    dependencies = [
        ("job", "0015_alter_jobcost_uom"),
    ]

    operations = [
        migrations.RunPython(ensure_uom_id, reverse_code=migrations.RunPython.noop),
    ]
