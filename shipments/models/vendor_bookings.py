from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from partners.models import Vendor
from core.models.currencies import Currency
from core.models.payment_terms import PaymentTerm
from geo.models import Location
from core.models.services import Service

from job.models.costs import JobCostType
from core.models.taxes import Tax
from core.utils.numbering import get_next_number
from job.models.job_orders import JobOrder
from partners.models import Vendor
from django.db.models import PROTECT, CASCADE
from django.utils import timezone
from core.models.currencies import Currency
from core.models.payment_terms import PaymentTerm  # 
from decimal import Decimal

class VendorBooking(models.Model):
    ST_DRAFT = "DRAFT"
    ST_CONFIRMED = "CONFIRMED"
    ST_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (ST_DRAFT, "Draft"),
        (ST_CONFIRMED, "Confirmed"),
        (ST_CANCELLED, "Cancelled"),
    ]

    booking_no = models.CharField(max_length=50, blank=True, default="")
    issued_date = models.DateField(default=timezone.localdate)
    job_order = models.ForeignKey("job.JobOrder", on_delete=CASCADE, related_name="vendor_bookings")

    vendor = models.ForeignKey(
        Vendor,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_index=True,
    )

    currency = models.ForeignKey(
        "core.Currency",  # sesuaikan path Currency om
        on_delete=PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    idr_rate = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
        default=None,
        help_text="Rate currency ke IDR (1 currency = X IDR).",
    )
    payment_term = models.ForeignKey(
        "core.PaymentTerm",  # sesuaikan path Currency om
        on_delete=PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    total_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    discount_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    discount_rate = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text="Informational only"
    )
    total_idr = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ST_DRAFT)

    created_by = models.ForeignKey(
        "auth.User", on_delete=PROTECT, related_name="+", null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_bookings"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking_no or 'DRAFT'} - {self.job_order_id}"

    
		

class VendorBookingLine(models.Model):
    booking = models.ForeignKey("shipments.VendorBooking", on_delete=CASCADE, related_name="lines")
    line_no = models.IntegerField(default=1)

    # ✅ "jenis cost procurement" (bukan produk sales)
    cost_type = models.ForeignKey(
        "job.JobCostType",
        on_delete=PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Jenis biaya/vendor work (master Cost Type). Dipilih dari modal.",
    )

    # ✅ cache schema modal (TRUCK/SEA/AIR/...)
    service_type = models.CharField(max_length=20, blank=True, default="")

    # ✅ auto description (editable)
    description = models.CharField(max_length=255, blank=True, default="")
    description_is_manual = models.BooleanField(default=False)

    qty = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))

    uom = models.CharField(max_length=20, blank=True, default="")
    
    details = models.JSONField(default=dict, blank=True)

    # ✅ idempotent generate from job cost
    source_job_cost = models.OneToOneField(
        "job.JobCost",  # sesuaikan nama model cost line om
        on_delete=PROTECT,
        related_name="vendor_booking_line",
        null=True,
        blank=True,
    )
    taxes = models.ManyToManyField(Tax, blank=True, related_name="booking_lines")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_booking_lines"
        ordering = ["booking_id", "line_no"]

    def __str__(self):
        return f"{self.booking_id}#{self.line_no}"
