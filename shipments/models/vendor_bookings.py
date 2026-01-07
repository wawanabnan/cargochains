from django.db import models
from django.conf import settings

from partners.models import Partner
from core.models.currencies import Currency
from core.models.payment_terms import PaymentTerm
from geo.models import Location
from core.models.services import Service

# Sesuaikan import Shipment kalau path di project om beda

# Sesuaikan CostType/Tax path kalau beda
from job.models.costs import JobCostType
from core.models.taxes import Tax


class VendorBooking(models.Model):
    # --- source type ---
    SRC_QUOTATION = "quotation"
    SRC_VERBAL = "verbal"
    SRC_RATE_CARD = "rate_card"
    SOURCE_CHOICES = [
        (SRC_QUOTATION, "Quotation"),
        (SRC_VERBAL, "Verbal / Phone"),
        (SRC_RATE_CARD, "Rate Card"),
    ]

    # --- status ---
    ST_DRAFT = "draft"
    ST_SENT = "sent"
    ST_CONFIRMED = "confirmed"
    ST_COMPLETED = "completed"
    ST_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (ST_DRAFT, "Draft"),
        (ST_SENT, "Sent"),
        (ST_CONFIRMED, "Confirmed"),
        (ST_COMPLETED, "Completed"),
        (ST_CANCELLED, "Cancelled"),
    ]

    number = models.CharField(max_length=30, unique=True)
    booking_date = models.DateField()

    vendor = models.ForeignKey(
        Partner, on_delete=models.PROTECT, related_name="vendor_bookings"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT)

    # FK + snapshot
    origin_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="+")
    origin_text = models.CharField(max_length=255)
    destination_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="+")
    destination_text = models.CharField(max_length=255)

    etd = models.DateField(null=True, blank=True)
    eta = models.DateField(null=True, blank=True)

    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.PROTECT)

    source_type = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SRC_VERBAL
    )

    remarks = models.TextField(blank=True)

    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=ST_DRAFT
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_vendor_bookings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-booking_date", "-id"]

    def __str__(self) -> str:
        return self.number

    def recalc_total(self, save=True):
        total = self.lines.aggregate(s=models.Sum("amount"))["s"] or 0
        self.total_amount = total
        if save:
            self.save(update_fields=["total_amount", "updated_at"])


class VendorBookingLine(models.Model):
    booking = models.ForeignKey(
        VendorBooking, on_delete=models.CASCADE, related_name="lines"
    )

    cost_type = models.ForeignKey(JobCostType, on_delete=models.PROTECT)
    description = models.CharField(max_length=255)

    qty = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    uom = models.CharField(max_length=20, default="LS")

    unit_price = models.DecimalField(max_digits=18, decimal_places=2)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # OPTIONAL expected VAT (not posted)
    expected_tax = models.ForeignKey(Tax, on_delete=models.PROTECT, null=True, blank=True)
    expected_tax_rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    expected_tax_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        self.amount = (self.qty or 0) * (self.unit_price or 0)

        if self.expected_tax:
            # snapshot rate: ambil dari tax kalau belum diisi
            if self.expected_tax_rate is None:
                rate = getattr(self.expected_tax, "rate", None)
                self.expected_tax_rate = rate
            if self.expected_tax_rate:
                self.expected_tax_amount = (self.amount * self.expected_tax_rate) / 100
            else:
                self.expected_tax_amount = None
        else:
            self.expected_tax_rate = None
            self.expected_tax_amount = None

        super().save(*args, **kwargs)

        # update total header (ringan)
        if self.booking_id:
            self.booking.recalc_total(save=True)
