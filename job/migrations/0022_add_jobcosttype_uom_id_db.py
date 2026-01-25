from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("job", "0021_remove_jobcost_uom_jobcosttype_uom"),  # sesuaikan kalau dependency kamu beda
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # tambah kolom kalau belum ada
                """
                ALTER TABLE job_cost_types
                ADD COLUMN uom_id BIGINT NULL;
                """,
                # index (optional tapi bagus)
                """
                CREATE INDEX job_cost_types_uom_id_idx ON job_cost_types (uom_id);
                """,
                # FK (optional; kalau tabel uoms benar dan kamu mau enforce)
                """
                ALTER TABLE job_cost_types
                ADD CONSTRAINT job_cost_types_uom_id_fk
                FOREIGN KEY (uom_id) REFERENCES uoms (id);
                """,
            ],
            reverse_sql=[
                # reverse: drop FK, index, column
                "ALTER TABLE job_cost_types DROP FOREIGN KEY job_cost_types_uom_id_fk;",
                "DROP INDEX job_cost_types_uom_id_idx ON job_cost_types;",
                "ALTER TABLE job_cost_types DROP COLUMN uom_id;",
            ],
        )
    ]
