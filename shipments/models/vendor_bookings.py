from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from partners.models import Partner
from core.models.currencies import Currency
from core.models.payment_terms import PaymentTerm
from geo.models import Location
from core.models.services import Service

from job.models.costs import JobCostType
from core.models.taxes import Tax
from core.utils.numbering import get_next_number
from job.models.job_orders import JobOrder
from partners.models import Vendor

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

    # ✅ boleh null (sementara), tapi hanya Draft
    job_order = models.ForeignKey(
        JobOrder,
        on_delete=models.PROTECT,
        related_name="vendor_bookings",
        null=True,
        blank=True,
    )

    number = models.CharField(max_length=30, unique=True)
    booking_date = models.DateField()

     # ✅ tambahan (boleh kosong)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_index=True,
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT)

    # ✅ Origin/Destination = segment route per booking (ops)
    # FK boleh kosong (kalau master Location belum lengkap / terlalu banyak), tetap ada snapshot text
    origin_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    origin_text = models.CharField(max_length=255, blank=True, default="")

    destination_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    destination_text = models.CharField(max_length=255, blank=True, default="")

    # ✅ ops instruction (bukan leg resmi)
    pickup_note = models.TextField(blank=True, default="")
    delivery_note = models.TextField(blank=True, default="")

    etd = models.DateField(null=True, blank=True)
    eta = models.DateField(null=True, blank=True)

    # ✅ currency di header saja
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.PROTECT)

    source_type = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SRC_VERBAL
    )

    remarks = models.TextField(blank=True, default="")
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
        db_table = "vendor_booking"

    def __str__(self) -> str:
        return self.number

    def clean(self):
        # ✅ booking boleh tanpa referensi, tapi hanya Draft
        if not self.job_order_id and self.status != self.ST_DRAFT:
            raise ValidationError(
                "Booking tanpa referensi hanya boleh status Draft. "
                "Silakan link ke Job Order dulu sebelum Sent/Confirmed/Completed."
            )

        # ops minimal: origin/destination wajib diisi via FK atau text
        if not (self.origin_location_id or (self.origin_text or "").strip()):
            raise ValidationError("Origin wajib diisi (pilih Location atau isi text).")
        if not (self.destination_location_id or (self.destination_text or "").strip()):
            raise ValidationError("Destination wajib diisi (pilih Location atau isi text).")

    def recalc_total(self, save=True):
        total = self.lines.aggregate(s=models.Sum("amount"))["s"] or 0
        self.total_amount = total
        if save:
            self.save(update_fields=["total_amount", "updated_at"])


    def save(self, *args, **kwargs):
        # ✅ auto numbering (sekali saat create)
        if not self.pk and not self.number:
            self.number = get_next_number("shipments", "VENDOR_BOOKING")
        super().save(*args, **kwargs)

class VendorBookingLine(models.Model):
    booking = models.ForeignKey(
        VendorBooking, on_delete=models.CASCADE, related_name="lines"
    )

    # ✅ item charge harus JobCostType (vendor-only)
    cost_type = models.ForeignKey(JobCostType, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")

    qty = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    uom = models.CharField(max_length=20, default="LS")

    unit_price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Optional expected VAT (not posted)
    estimated_tax = models.ForeignKey(
        Tax, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    estimated_tax_rate = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    estimated_tax_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        db_table = "vendor_booking_lines"

    def clean(self):
        # ✅ internal cost type tidak boleh masuk booking line
        if self.cost_type_id:
            if getattr(self.cost_type, "requires_vendor", True) is False:
                raise ValidationError(
                    "Cost Type internal tidak boleh dibuat Vendor Booking Line."
                )
            if getattr(self.cost_type, "is_active", True) is False:
                raise ValidationError("Cost Type tidak aktif.")

    def save(self, *args, **kwargs):
        # amount
        self.amount = (self.qty or 0) * (self.unit_price or 0)

        # expected tax snapshot
        if self.expected_tax:
            if self.expected_tax_rate is None:
                self.expected_tax_rate = getattr(self.expected_tax, "rate", None)

            if self.expected_tax_rate:
                self.expected_tax_amount = (self.amount * self.expected_tax_rate) / 100
            else:
                self.expected_tax_amount = None
        else:
            self.expected_tax_rate = None
            self.expected_tax_amount = None

        super().save(*args, **kwargs)

        # update total header
        if self.booking_id:
            self.booking.recalc_total(save=True)
