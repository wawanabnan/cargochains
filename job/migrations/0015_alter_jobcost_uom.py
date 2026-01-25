from django.db import migrations

def ensure_uom_id(apps, schema_editor):
    table = "job_costs"

    schema_editor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = 'uom_id'
        """,
        [table],
    )
    exists = schema_editor.cursor.fetchone()[0] > 0

    if not exists:
        # GANTI BIGINT -> INT kalau PK tabel UOM kamu INT
        schema_editor.execute(f"ALTER TABLE {table} ADD COLUMN uom_id BIGINT NOT NULL")

class Migration(migrations.Migration):
    dependencies = [
        ("job", "0014_jobcost_tax_jobcost_uom_jobcosttype_taxes_and_more"),
    ]

    operations = [
        migrations.RunPython(ensure_uom_id, reverse_code=migrations.RunPython.noop),
    ]
