# shipments/models/event.py
from django.conf import settings
from django.db import models
from django.utils import timezone

class EventCode(models.TextChoices):
    SHIPMENT_CREATED = "SHIPMENT_CREATED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    PICKUP_DISPATCHED = "PICKUP_DISPATCHED"
    PICKUP_COMPLETED = "PICKUP_COMPLETED"
    DEPARTED = "DEPARTED"
    ARRIVED = "ARRIVED"
    OUTFORDELIVERY = "OUTFORDELIVERY"
    DELIVERED = "DELIVERED"
    POD_UPLOADED = "POD_UPLOADED"
    EXCEPTION = "EXCEPTION"
    EXCEPTION_RESOLVED = "EXCEPTION_RESOLVED"
    CANCELED = "CANCELED"

class ShipmentEvent(models.Model):
    shipment = models.ForeignKey("shipments.Shipment", on_delete=models.CASCADE, related_name="events")
    leg = models.ForeignKey("shipments.ShipmentLeg", null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    trip = models.ForeignKey("shipments.ShipmentLegTrip", null=True, blank=True, on_delete=models.SET_NULL, related_name="events")

    code = models.CharField(max_length=64, choices=EventCode.choices, db_index=True)
    event_time = models.DateTimeField(default=timezone.now, db_index=True)
    location_text = models.CharField(max_length=255, null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    is_public = models.BooleanField(default=False, db_index=True)
    affects_status = models.BooleanField(default=True)
    dedupe_key = models.CharField(max_length=120, null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    source = models.CharField(max_length=32, default="OPS")  # OPS / SYSTEM / INTEGRATION
    source_ref = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["shipment", "event_time"]),
            models.Index(fields=["shipment", "is_public", "event_time"]),
        ]

    def __str__(self):
       sn = self.shipment.shipment_number or self.shipment.tracking_no
       return f"{sn} {self.code} @ {self.event_time}"

