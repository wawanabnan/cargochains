from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import PROTECT, CASCADE, Max, Sum
from django.utils import timezone

from partners.models import Vendor
from core.models.currencies import Currency
from core.models.payment_terms import PaymentTerm
from geo.models import Location
from core.models.services import Service
from core.models.taxes import Tax
from core.utils.numbering import get_next_number

from job.constants import SYSTEM_GROUP_CHOICES
from job.models.job_orders import JobOrder
from job.models.costs import JobCost, JobCostType


# ============================================================
# Helpers
# ============================================================

Q2 = Decimal("0.01")


def q2(x):
    return Decimal(x or 0).quantize(Q2, rounding=ROUND_HALF_UP)


def compute_line_tax_amount(line) -> Decimal:
    """
    Hitung total pajak add-on dari VendorBookingLine.taxes
    Asumsi Tax punya field `rate` (%)
    """
    base = Decimal(line.amount or 0)
    total = Decimal("0")

    for t in line.taxes.all():
        rate = Decimal(getattr(t, "rate", 0) or 0) / Decimal("100")
        total += base * rate

    return q2(total)


def recompute_vendor_booking_totals(vb):
    """
    Header totals:
    subtotal = sum(amount)
    tax      = sum(pajak per line)
    wht      = subtotal * wht_rate
    total    = subtotal + tax - wht
    """
    subtotal = vb.lines.aggregate(s=Sum("amount"))["s"] or Decimal("0")

    tax_total = Decimal("0")
    for ln in vb.lines.all().prefetch_related("taxes"):
        tax_total += compute_line_tax_amount(ln)

    tax_total = q2(tax_total)

    wht_rate = Decimal(getattr(vb, "wht_rate", 0) or 0) / Decimal("100")
    wht_amount = q2(subtotal * wht_rate)

    vb.subtotal_amount = q2(subtotal)
    vb.tax_amount = tax_total
    vb.wht_amount = wht_amount
    vb.total_amount = q2(vb.subtotal_amount + vb.tax_amount - vb.wht_amount)

    vb.save(
        update_fields=[
            "subtotal_amount",
            "tax_amount",
            "wht_amount",
            "total_amount",
        ]
    )


# ============================================================
# VendorBooking (HEADER)
# ============================================================

class VendorBooking(models.Model):
    ST_DRAFT = "DRAFT"
    ST_CONFIRMED = "CONFIRMED"
    ST_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (ST_DRAFT, "Draft"),
        (ST_CONFIRMED, "Confirmed"),
        (ST_CANCELLED, "Cancelled"),
    ]

    vb_number = models.CharField(max_length=50, blank=True, default="")
    letter_number = models.CharField(max_length=50, blank=True, default="")
    issued_date = models.DateField(default=timezone.localdate)

    job_order = models.ForeignKey(
        JobOrder, on_delete=CASCADE, related_name="vendor_bookings"
    )

    booking_group = models.CharField(
        max_length=50,
        choices=SYSTEM_GROUP_CHOICES,
        db_index=True,
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    idr_rate = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
        default=None,
    )

    wht_rate = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )

    wht_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )

    payment_term = models.ForeignKey(
        PaymentTerm,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    subtotal_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )

    tax_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )

    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
    )

    discount_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
    )

    header_json = models.JSONField(default=dict, blank=True)

    LETTER_SEA_SI = "SEA_SI"
    LETTER_AIR_SLI = "AIR_SLI"
    LETTER_TRUCK_TO = "TRUCK_TO"

    LETTER_TYPE_CHOICES = [
        (LETTER_SEA_SI, "Shipping Instruction (Sea)"),
        (LETTER_AIR_SLI, "Shipping Letter of Instruction (Air)"),
        (LETTER_TRUCK_TO, "Trucking Order"),
    ]

    letter_type = models.CharField(
        max_length=20,
        choices=LETTER_TYPE_CHOICES,
        default=LETTER_TRUCK_TO,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ST_DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_bookings"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.vb_number or 'DRAFT'} - {self.job_order_id}"

    def save(self, *args, **kwargs):
        creating = self.pk is None

        if not self.issued_date:
            self.issued_date = timezone.localdate()

        if creating:
            if not self.vb_number:
                self.vb_number = get_next_number("shipments", "VENDOR_BOOKING")

            if not self.letter_number:
                self.letter_number = get_next_number("shipments", self.letter_type)

        super().save(*args, **kwargs)


# ============================================================
# VendorBookingLine (LINES)
# ============================================================

class VendorBookingLine(models.Model):
    vendor_booking = models.ForeignKey(
        VendorBooking,
        on_delete=CASCADE,
        related_name="lines",
    )

    job_cost = models.ForeignKey(
        JobCost,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    cost_type = models.ForeignKey(
        JobCostType,
        on_delete=PROTECT,
        related_name="+",
    )

    description = models.CharField(max_length=255, blank=True, default="")

    qty = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("1"),
    )

    unit_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
    )

    uom = models.CharField(max_length=20, blank=True, default="")
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )

    cost_group = models.CharField(max_length=50, blank=True, default="")

    taxes = models.ManyToManyField(
        Tax,
        blank=True,
        related_name="vendor_booking_lines",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_booking_lines"
        ordering = ["vendor_booking_id", "id"]

    
    def save(self, *args, **kwargs):
        if self.unit_price is not None and self.qty is not None:
            self.amount = q2(Decimal(self.qty) * Decimal(self.unit_price))

        super().save(*args, **kwargs)

    def base_amount(self):
        return q2(self.amount)

    def tax_amount(self):
        return compute_line_tax_amount(self)

    def line_total(self):
        return q2(self.base_amount() + self.tax_amount())
    

    from django.core.exceptions import ValidationError

    def clean(self):
        # 1) JobCost wajib
        if not self.job_cost_id:
            raise ValidationError("Job Cost wajib diisi.")

        # 2) Validasi konsistensi Job Order pakai DB-safe lookup (anti instance kosong)
        if self.vendor_booking_id and self.job_cost_id:
            vb_job_id = (
                VendorBooking.objects
                .filter(pk=self.vendor_booking_id)
                .values_list("job_order_id", flat=True)
                .first()
            )
            jc_job_id = (
                JobCost.objects
                .filter(pk=self.job_cost_id)
                .values_list("job_order_id", flat=True)
                .first()
            )

            # kalau salah satu tidak ketemu, kasih error jelas
            if not vb_job_id:
                raise ValidationError("Vendor Booking tidak valid.")
            if not jc_job_id:
                raise ValidationError("Job Cost tidak valid.")

            if vb_job_id != jc_job_id:
                raise ValidationError("Job Cost tidak sesuai Job Order.")

        # 3) (opsional tapi bagus) vendor harus sama juga
        if self.vendor_booking_id and self.job_cost_id:
            vb_vendor_id = (
                VendorBooking.objects
                .filter(pk=self.vendor_booking_id)
                .values_list("vendor_id", flat=True)
                .first()
            )
            jc_vendor_id = (
                JobCost.objects
                .filter(pk=self.job_cost_id)
                .values_list("vendor_id", flat=True)
                .first()
            )

            # Kalau jobcost punya vendor, dan VB punya vendor, harus match
            if vb_vendor_id and jc_vendor_id and vb_vendor_id != jc_vendor_id:
                raise ValidationError("Vendor pada Job Cost tidak sesuai Vendor Booking.")

