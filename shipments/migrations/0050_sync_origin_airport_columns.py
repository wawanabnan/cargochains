from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("shipments", "0049_sync_origin_port_columns"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE shipments_shipment
                            ADD COLUMN origin_airport_id BIGINT NULL,
                            ADD COLUMN destination_airport_id BIGINT NULL;

                        CREATE INDEX shipments_shipment_origin_airport_id_idx
                            ON shipments_shipment(origin_airport_id);

                        CREATE INDEX shipments_shipment_destination_airport_id_idx
                            ON shipments_shipment(destination_airport_id);
                    """,
                    reverse_sql="""
                        ALTER TABLE shipments_shipment
                            DROP COLUMN origin_airport_id,
                            DROP COLUMN destination_airport_id;

                        DROP INDEX shipments_shipment_origin_airport_id_idx
                            ON shipments_shipment;

                        DROP INDEX shipments_shipment_destination_airport_id_idx
                            ON shipments_shipment;
                    """,
                ),
            ],
            state_operations=[],
        ),
    ]
