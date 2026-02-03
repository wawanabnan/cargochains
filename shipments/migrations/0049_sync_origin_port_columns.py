from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("shipments", "0048_alter_shipment_table"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE shipments_shipment
                            ADD COLUMN origin_port_id BIGINT NULL,
                            ADD COLUMN destination_port_id BIGINT NULL;

                        CREATE INDEX shipments_shipment_origin_port_id_idx
                            ON shipments_shipment(origin_port_id);

                        CREATE INDEX shipments_shipment_destination_port_id_idx
                            ON shipments_shipment(destination_port_id);
                    """,
                    reverse_sql="""
                        ALTER TABLE shipments_shipment
                            DROP COLUMN origin_port_id,
                            DROP COLUMN destination_port_id;

                        DROP INDEX shipments_shipment_origin_port_id_idx
                            ON shipments_shipment;

                        DROP INDEX shipments_shipment_destination_port_id_idx
                            ON shipments_shipment;
                    """,
                ),
            ],
            state_operations=[],
        ),
    ]
