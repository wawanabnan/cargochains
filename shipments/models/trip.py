# shipments/models/trip.py
from django.db import models

class TripStatus(models.TextChoices):
    PLANNED = "PLANNED"
    DISPATCHED = "DISPATCHED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    EXCEPTION = "EXCEPTION"
    CANCELED = "CANCELED"

class ShipmentLegTrip(models.Model):
    leg = models.ForeignKey("shipments.ShipmentLeg", on_delete=models.CASCADE, related_name="trips")
    seq = models.PositiveIntegerField()

    truck_size = models.CharField(max_length=32, null=True, blank=True)
    vehicle_type = models.CharField(max_length=32, null=True, blank=True)

    # Optional, aman pakai string ref
    vendor = models.ForeignKey("partners.Vendor", null=True, blank=True, on_delete=models.SET_NULL)
    driver_name = models.CharField(max_length=128, null=True, blank=True)
    plate_no = models.CharField(max_length=32, null=True, blank=True)

    planned_pickup = models.DateTimeField(null=True, blank=True)
    planned_dropoff = models.DateTimeField(null=True, blank=True)
    actual_pickup = models.DateTimeField(null=True, blank=True)
    actual_dropoff = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=TripStatus.choices, default=TripStatus.PLANNED, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["leg", "seq"], name="uq_trip_leg_seq"),
        ]
        indexes = [
            models.Index(fields=["leg", "status"]),
        ]

    def __str__(self):
        return f"{self.leg} trip#{self.seq}"

