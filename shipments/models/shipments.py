from django.conf import settings
from django.db import models
from geo.models import Location
from core.models.services import Service
from core.utils.numbering import get_next_number

import secrets
ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

def generate_tracking_no(n=10):
     return "".join(secrets.choice(ALPH) for _ in range(n))

class ShipmentStatus(models.TextChoices):
    DRAFT = "DRAFT"
    PICKUP = "PICKUP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    EXCEPTION = "EXCEPTION"
    CANCELED = "CANCELED"

class Shipment(models.Model):
    shipment_number = models.CharField(max_length=20, unique=True, db_index=True,null=True, blank=True)  # internal
    tracking_no = models.CharField(
        null=True,
        blank=True,
        max_length=20, unique=True, db_index=True)  # SHP-YYMM-XXXXXX

    # Gunakan string ref supaya tidak hard-import dan aman saat app loading
    job_order = models.ForeignKey("job.JobOrder", 
            on_delete=models.PROTECT, related_name="shipments",
            null=True,
            blank=True,
            )
    service = models.ForeignKey(
        "core.Service",   # sesuaikan app.model
        on_delete=models.PROTECT,
        related_name="shipments_services",
        null=True, blank=True,   # sementara demi migrasi
    )


    origin = models.ForeignKey("geo.Location", on_delete=models.PROTECT, related_name="shipments_origin")
    destination = models.ForeignKey("geo.Location", on_delete=models.PROTECT, related_name="shipments_destination")

    # Node operasional (optional) untuk multimodal accuracy
    origin_port = models.ForeignKey(
        "geo.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="shipments_origin_port",
    )

    destination_port = models.ForeignKey(
        "geo.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="shipments_destination_port",
    )

    origin_airport = models.ForeignKey(
        "geo.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="shipments_origin_airport",
    )

    destination_airport = models.ForeignKey(
        "geo.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="shipments_destination_airport",
    )

    status = models.CharField(max_length=32, choices=ShipmentStatus.choices, default=ShipmentStatus.DRAFT, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="shipments_created")

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]
        db_table = "shipments_shipment"
    
    def __str__(self):
        return self.shipment_number or self.tracking_no or f"Shipment#{self.pk}"


    
    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if not self.shipment_number:
            self.shipment_number = get_next_number("shipments", "SHIPMENT")

        super().save(*args, **kwargs)

         # import di bawah supaya aman dari circular import
        from shipments.services.legs import generate_default_legs
        from shipments.models import ShipmentEvent

        # Generate legs jika data lokasi lengkap dan legs belum ada
        if self.service_id and self.origin_id and self.destination_id:
            if is_new or not self.legs.exists():
                generate_default_legs(self, overwrite=False)

        # Event awal: hanya sekali
        if is_new:
            ShipmentEvent.objects.get_or_create(
                shipment=self,
                code="SHIPMENT_CREATED",
                is_public=False,
                affects_status=False,  # IMPORTANT
                note="Shipment created",
                dedupe_key=f"shipment_created:{self.pk}"  # optional
            )



        if not self.tracking_no:
            # generate unique tracking no
            code = generate_tracking_no(10)
            from shipments.models import Shipment  # kalau perlu, tapi sebaiknya pakai self.__class__
            while self.__class__.objects.filter(tracking_no=code).exists():
                code = generate_tracking_no(10)
            self.tracking_no = code

    