# Generated manually for clean tracking tables

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0027_coresetting_text_value"),
        ("geo", "0007_location_altitude_location_country_code_and_more"),
        ("job", "0032_alter_joborder_customer_note_alter_joborder_sla_note"),
        ("partners", "0013_alter_partner_address_alter_partner_address_line1_and_more"),
        ("shipments", "0045_shipmentsequence_remove_shipmentroute_carrier_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ------------------------------------------------------------------
        # 0) Shipment (entity utama)
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="Shipment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("tracking_no", models.CharField(
                    max_length=20,
                    unique=True,
                    null=True,
                    blank=True,
                    db_index=True,
                )),
                ("status", models.CharField(
                    max_length=32,
                    default="DRAFT",
                    db_index=True,
                    choices=[
                        ("DRAFT", "Draft"),
                        ("PICKUP", "Pickup"),
                        ("IN_TRANSIT", "In Transit"),
                        ("OUT_FOR_DELIVERY", "Out For Delivery"),
                        ("DELIVERED", "Delivered"),
                        ("EXCEPTION", "Exception"),
                        ("CANCELED", "Canceled"),
                    ],
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(
                    to=settings.AUTH_USER_MODEL,
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="shipments_created",
                )),
                ("job_order", models.ForeignKey(
                    to="job.joborder",
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="shipments",
                )),
                ("service", models.ForeignKey(
                    to="core.service",
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="shipments",
                )),
                ("origin", models.ForeignKey(
                    to="geo.location",
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="shipments_origin",
                )),
                ("destination", models.ForeignKey(
                    to="geo.location",
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="shipments_destination",
                )),
            ],
        ),

        migrations.AddIndex(
            model_name="shipment",
            index=models.Index(
                fields=["created_at"],
                name="shipments_created_at_idx",
            ),
        ),

        # ------------------------------------------------------------------
        # 1) ShipmentSequence
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="ShipmentSequence",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("yymm", models.CharField(max_length=4, unique=True)),
                ("last_number", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),

        # ------------------------------------------------------------------
        # 2) ShipmentLeg
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="ShipmentLeg",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("seq", models.PositiveIntegerField()),
                ("mode", models.CharField(
                    max_length=16,
                    choices=[
                        ("TRUCK", "Truck"),
                        ("SEA", "Sea"),
                        ("AIR", "Air"),
                    ],
                )),
                ("planned_departure", models.DateTimeField(null=True, blank=True)),
                ("planned_arrival", models.DateTimeField(null=True, blank=True)),
                ("actual_departure", models.DateTimeField(null=True, blank=True)),
                ("actual_arrival", models.DateTimeField(null=True, blank=True)),
                ("status", models.CharField(
                    max_length=16,
                    default="PLANNED",
                    db_index=True,
                    choices=[
                        ("PLANNED", "Planned"),
                        ("IN_PROGRESS", "In Progress"),
                        ("COMPLETED", "Completed"),
                        ("EXCEPTION", "Exception"),
                        ("CANCELED", "Canceled"),
                    ],
                )),
                ("shipment", models.ForeignKey(
                    to="shipments.shipment",
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="legs",
                )),
                ("from_location", models.ForeignKey(
                    to="geo.location",
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="legs_from",
                )),
                ("to_location", models.ForeignKey(
                    to="geo.location",
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="legs_to",
                )),
            ],
        ),

        migrations.AddConstraint(
            model_name="shipmentleg",
            constraint=models.UniqueConstraint(
                fields=("shipment", "seq"),
                name="uq_leg_shipment_seq",
            ),
        ),

        # ------------------------------------------------------------------
        # 3) ShipmentLegTrip
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="ShipmentLegTrip",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("seq", models.PositiveIntegerField()),
                ("truck_size", models.CharField(max_length=32, null=True, blank=True)),
                ("vehicle_type", models.CharField(max_length=32, null=True, blank=True)),
                ("driver_name", models.CharField(max_length=128, null=True, blank=True)),
                ("plate_no", models.CharField(max_length=32, null=True, blank=True)),
                ("planned_pickup", models.DateTimeField(null=True, blank=True)),
                ("planned_dropoff", models.DateTimeField(null=True, blank=True)),
                ("actual_pickup", models.DateTimeField(null=True, blank=True)),
                ("actual_dropoff", models.DateTimeField(null=True, blank=True)),
                ("status", models.CharField(
                    max_length=16,
                    default="PLANNED",
                    db_index=True,
                    choices=[
                        ("PLANNED", "Planned"),
                        ("DISPATCHED", "Dispatched"),
                        ("PICKED_UP", "Picked Up"),
                        ("IN_TRANSIT", "In Transit"),
                        ("ARRIVED", "Arrived"),
                        ("COMPLETED", "Completed"),
                        ("EXCEPTION", "Exception"),
                        ("CANCELED", "Canceled"),
                    ],
                )),
                ("leg", models.ForeignKey(
                    to="shipments.shipmentleg",
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="trips",
                )),
                ("vendor", models.ForeignKey(
                    to="partners.vendor",
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                )),
            ],
        ),

        migrations.AddConstraint(
            model_name="shipmentlegtrip",
            constraint=models.UniqueConstraint(
                fields=("leg", "seq"),
                name="uq_trip_leg_seq",
            ),
        ),

        # ------------------------------------------------------------------
        # 4) ShipmentEvent
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="ShipmentEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("code", models.CharField(
                    max_length=64,
                    db_index=True,
                    choices=[
                        ("SHIPMENT_CREATED", "Shipment Created"),
                        ("PICKUP_SCHEDULED", "Pickup Scheduled"),
                        ("PICKUP_DISPATCHED", "Pickup Dispatched"),
                        ("PICKUP_COMPLETED", "Pickup Completed"),
                        ("DEPARTED", "Departed"),
                        ("ARRIVED", "Arrived"),
                        ("OUTFORDELIVERY", "Out For Delivery"),
                        ("DELIVERED", "Delivered"),
                        ("POD_UPLOADED", "POD Uploaded"),
                        ("EXCEPTION", "Exception"),
                        ("EXCEPTION_RESOLVED", "Exception Resolved"),
                        ("CANCELED", "Canceled"),
                    ],
                )),
                ("event_time", models.DateTimeField(
                    default=django.utils.timezone.now,
                    db_index=True,
                )),
                ("location_text", models.CharField(max_length=255, null=True, blank=True)),
                ("note", models.TextField(null=True, blank=True)),
                ("is_public", models.BooleanField(default=False, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("source", models.CharField(max_length=32, default="OPS")),
                ("source_ref", models.CharField(max_length=64, null=True, blank=True)),
                ("shipment", models.ForeignKey(
                    to="shipments.shipment",
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="events",
                )),
                ("leg", models.ForeignKey(
                    to="shipments.shipmentleg",
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="events",
                )),
                ("trip", models.ForeignKey(
                    to="shipments.shipmentlegtrip",
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="events",
                )),
                ("created_by", models.ForeignKey(
                    to=settings.AUTH_USER_MODEL,
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                )),
            ],
        ),

        # ------------------------------------------------------------------
        # 5) ShipmentDocument
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="ShipmentDocument",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("doc_type", models.CharField(max_length=32, db_index=True)),
                ("file", models.FileField(upload_to="shipment_docs/%Y/%m/")),
                ("is_public", models.BooleanField(default=False)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("shipment", models.ForeignKey(
                    to="shipments.shipment",
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="documents",
                )),
                ("uploaded_by", models.ForeignKey(
                    to=settings.AUTH_USER_MODEL,
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                )),
            ],
        ),
    ]
