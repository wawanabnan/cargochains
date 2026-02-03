# shipments/models/leg.py
from django.db import models
from geo.models import Location


class LegMode(models.TextChoices):
    TRUCK = "TRUCK"
    SEA = "SEA"
    AIR = "AIR"

class LegStatus(models.TextChoices):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EXCEPTION = "EXCEPTION"
    CANCELED = "CANCELED"

class ShipmentLeg(models.Model):
    shipment = models.ForeignKey("shipments.Shipment", on_delete=models.CASCADE, related_name="legs")
    seq = models.PositiveIntegerField()

    mode = models.CharField(max_length=16, choices=LegMode.choices)
    from_location = models.ForeignKey("geo.Location", on_delete=models.PROTECT, related_name="legs_from")
    to_location = models.ForeignKey("geo.Location", on_delete=models.PROTECT, related_name="legs_to")

    planned_departure = models.DateTimeField(null=True, blank=True)
    planned_arrival = models.DateTimeField(null=True, blank=True)
    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=LegStatus.choices, default=LegStatus.PLANNED, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["shipment", "seq"], name="uq_leg_shipment_seq"),
        ]
        indexes = [
            models.Index(fields=["shipment", "status"]),
        ]

    def __str__(self):
        sn = self.shipment.shipment_number or self.shipment.tracking_no
        return f"{sn} leg#{self.seq}"
