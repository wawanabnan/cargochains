# app/models/shipping_instruction.py (atau sesuai struktur project)

from django.conf import settings
from django.db import models
from django.db.models import Max
from django.utils import timezone
from job.models.job_orders import JobOrder
from work_orders.models.vendor_bookings import VendorBooking
from core.utils.numbering import get_next_number

class ShippingInstructionDocument(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        CANCELLED = "CANCELLED", "Cancelled"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    vendor_booking = models.OneToOneField(
        "work_orders.VendorBooking",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="shipping_instruction",
    )
    job_order = models.ForeignKey(
        "job.JobOrder",
        on_delete=models.PROTECT,
        related_name="job_order_documents",
    )

  
    # numbering per type: SI001, SI002...
    sequence_no = models.PositiveIntegerField()
    document_no = models.CharField(max_length=30, unique=True)

    letter_date = models.DateField(default=timezone.localdate)

    # shipper = 3PL (auto snapshot)
    shipper_name = models.CharField(max_length=255)
    shipper_address = models.TextField(blank=True)

    # customer snapshot (boleh kosong kalau belum siap, tapi idealnya diisi saat confirm)
    customer_name = models.CharField(max_length=255, blank=True)
    customer_address = models.TextField(blank=True)

    reference_no = models.CharField(max_length=50, blank=True)

    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        constraints = [
        models.UniqueConstraint(fields=["sequence_no"], name="uniq_si_sequence_no"),
    ]

   
    

    def save(self, *args, **kwargs):
        if not self.document_no:
            self.document_no = get_next_number("shipments","SEA_SI",
            )
        super().save(*args, **kwargs)


class SeaShippingInstructionDetail(models.Model):
    document = models.OneToOneField(
        ShippingInstructionDocument,
        on_delete=models.PROTECT,
        related_name="sea_detail",
    )

    carrier_name = models.CharField(max_length=255, blank=True)
    vessel_name = models.CharField(max_length=255, blank=True)
    voyage_no = models.CharField(max_length=50, blank=True)

    pol = models.CharField(max_length=255, blank=True)  # port of loading
    pod = models.CharField(max_length=255, blank=True)  # port of discharge
    final_destination = models.CharField(max_length=255, blank=True)

    etd = models.DateField(blank=True, null=True)
    eta = models.DateField(blank=True, null=True)

    special_instructions = models.TextField(blank=True)
