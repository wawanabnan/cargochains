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
from job.models.job_costs import JobCost, JobCostType
from core.models.uoms import UOM
from django_summernote.fields import SummernoteTextField

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


class ServiceOrderMode(models.TextChoices):
    GENERAL = "GENERAL", "General"
    SEA = "SEA", "Sea"
    AIR = "AIR", "Air"
    INLAND = "INLAND", "Inland"


# ============================================================

# ============================================================
# VendorBooking (HEADER)
# ============================================================
class VendorBooking(models.Model):

    ST_DRAFT = "DRAFT"
    ST_SUBMITTED = "SUBMITTED"
    ST_REJECTED = "REJECTED"     # ✅ baru
    ST_APPROVED = "APPROVED"
    ST_SENT = "SENT"
    ST_CANCELLED = "CANCELLED"
    ST_CONFIRMED = "CONFIRMED"
    ST_DONE = "DONE"             # ✅ baru

    # NOTE: ST_CLOSED dibiarkan supaya data lama aman (optional deprecate)
    ST_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (ST_DRAFT, "Draft"),
        (ST_SUBMITTED, "Submitted"),
        (ST_REJECTED, "Rejected"),
        (ST_APPROVED, "Approved"),
        (ST_SENT, "Sent to Vendor"),
        (ST_CANCELLED, "Cancelled"),
        (ST_CONFIRMED, "Confirmed"),
        (ST_DONE, "Done"),

        # legacy / optional
        (ST_CLOSED, "Closed"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ST_DRAFT)

    booking_date = models.DateField(default=timezone.localdate, db_index=True)

    # ===== Submitted =====
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=PROTECT, related_name="+"
    )

    # ===== Rejected (✅ baru) =====
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=PROTECT, related_name="+"
    )
    reject_reason = models.TextField(blank=True, default="")

    # ===== Approved =====
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=PROTECT, related_name="+"
    )

    # ===== Sent =====
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=PROTECT, related_name="+"
    )
    sent_via = models.CharField(max_length=20, blank=True, default="")  # EMAIL/WA/MANUAL
    sent_to = models.CharField(max_length=255, blank=True, default="")

    # ===== Cancelled =====
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=PROTECT, related_name="+"
    )
    cancel_reason = models.TextField(blank=True, default="")

    # ===== Done (✅ baru) =====
    done_at = models.DateTimeField(null=True, blank=True)
    done_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=PROTECT, related_name="+"
    )

    # ===== Closed (legacy) =====
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=PROTECT, related_name="+"
    )

#=======================================================================    
    vb_number = models.CharField(max_length=50, blank=True, default="")
    
    job_order = models.ForeignKey(
        JobOrder, on_delete=CASCADE, related_name="vendor_bookings"
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
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    discount_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    vendor_note = SummernoteTextField(
        blank=True,
        default="",
        help_text="Catatan untuk vendor (Service Order)"
    )
    term_conditions = SummernoteTextField(
        blank=True,
        default="",
        help_text="Syarat & ketentuan Service Order"
    )


    service_order_mode = models.CharField(
        max_length=20,
        choices=ServiceOrderMode.choices,
        default=ServiceOrderMode.GENERAL,
        db_index=True,
        help_text="Mode Service Order untuk generate dokumen lanjutan"
    )


    class Meta:
        db_table = "vendor_bookings"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.vb_number or 'DRAFT'} - {self.job_order_id}"

    def save(self, *args, **kwargs):
        creating = self.pk is None


        if creating:
            if not self.vb_number:
                self.vb_number = get_next_number("shipments", "VENDOR_BOOKING")

    
        super().save(*args, **kwargs)


    def _tax_amount_group(self, group: str) -> Decimal:
        total = Decimal("0")
        q2 = Decimal("0.01")
        g = (group or "").upper()

        for ln in self.lines.all():   # <-- cukup all()
            base = Decimal(ln.amount or 0)
            for t in ln.taxes.all():
                if (t.group or "").upper() == g:
                    rate = Decimal(t.rate or 0)
                    total += (base * (rate / Decimal("100"))).quantize(q2, rounding=ROUND_HALF_UP)

        return total


    @property
    def ppn_amount(self) -> Decimal:
        return self._tax_amount_group("PPN")

    @property
    def pph_amount(self) -> Decimal:
        return self._tax_amount_group("PPH")


    @property
    def ppn_label_rate_display(self) -> str:
        rates = set()
        for ln in self.lines.prefetch_related("taxes").all():
            for t in ln.taxes.all():
                if (t.group or "").upper() == "PPN":
                    r = t.rate
                    if r is not None:
                        rates.add(str(r.normalize() if hasattr(r, "normalize") else r))
        if not rates:
            return "-"
        rates = sorted(rates, key=lambda x: Decimal(x))
        return f"PPN " + " + ".join([x + "%" for x in rates])

    @property
    def pph_label_rate_display(self) -> str:
        rates = set()
        for ln in self.lines.prefetch_related("taxes").all():
            for t in ln.taxes.all():
                if (t.group or "").upper() == "PPH":
                    r = t.rate
                    if r is not None:
                        rates.add(str(r.normalize() if hasattr(r, "normalize") else r))
        if not rates:
            return "-"
        rates = sorted(rates, key=lambda x: Decimal(x))
        return f"PPH " + " + ".join([x + "%" for x in rates])

    @property
    def print_grand_total(self) -> Decimal:
        # rule om: grand total = subtotal + ppn - pph - discount
        subtotal = self.subtotal_amount or Decimal("0")
        discount = self.discount_amount or Decimal("0")
        return subtotal + (self.ppn_amount or Decimal("0")) - (self.pph_amount or Decimal("0")) - discount


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

    uom_code = models.CharField(max_length=20, blank=True, default="")
    uom = models.ForeignKey(
        UOM,
        related_name="vb_line_uoms",
        on_delete=PROTECT,
        null=True,
        blank=True,
        help_text="Default UOM untuk cost line (mis: LS, TRIP, CNTR, CBM, KG)"
    )
  
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


from django.conf import settings
from django.db import models
from work_orders.models.vendor_bookings import VendorBooking


class ServiceOrderAttachment(models.Model):
    service_order = models.ForeignKey(
        VendorBooking,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Service Order Attachment",
    )

    file = models.FileField(
        upload_to="service_orders/%Y/%m/",
        verbose_name="File",
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Misal: Quotation Vendor, Booking Confirmation, dll."
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_order_attachments",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Service Order Attachment"
        verbose_name_plural = "Service Order Attachments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"SO #{self.service_order_id} - {self.filename}"

    @property
    def filename(self):
        return self.file.name.split("/")[-1]
