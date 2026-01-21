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
from job.constants import SYSTEM_GROUP_CHOICES,CostGroup
from django.db.models import Max
from django.core.validators import MinValueValidator
from job.models.costs import JobCost
from django.db.models import Sum
from decimal import Decimal, ROUND_HALF_UP



Q2 = Decimal("0.01")

def q2(x):
    return Decimal(x or 0).quantize(Q2, rounding=ROUND_HALF_UP)

def compute_line_tax_amount(line) -> Decimal:
    base = Decimal(line.amount or 0)
    total = Decimal("0")
    for t in line.taxes.all():
        rate = Decimal(getattr(t, "rate", 0) or 0) / Decimal("100")
        total += (base * rate)
    return q2(total)


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
    letter_number=models.CharField(max_length=50, blank=True, default="")
    issued_date = models.DateField(default=timezone.localdate)
    job_order = models.ForeignKey("job.JobOrder", on_delete=CASCADE, related_name="vendor_bookings")

    booking_group = models.CharField(
        max_length=50,
        choices=SYSTEM_GROUP_CHOICES,
        null=False,
        blank=False,
        db_index=True,
        help_text="Booking Type. Mengunci semua line dalam satu service group.",
    )
    
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

    idr_rate = models.DecimalField(max_digits=18, decimal_places=6, default=1)

    idr_rate = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
        default=None,
        help_text="Rate currency ke IDR (1 currency = X IDR).",
    )
    wht_rate = models.DecimalField(
        max_digits=9, decimal_places=6,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
        help_text="PPh/WHT rate (%) dipotong dari pembayaran (mis: 2.0, 4.0)"
    )
    wht_amount = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
        help_text="Nilai PPh/WHT (auto dari rate x base)"
    )
    payment_term = models.ForeignKey(
        "core.PaymentTerm",  # sesuaikan path Currency om
        on_delete=PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    subtotal_amount = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
        help_text="Jumlah sebelum pajak & wht"
    )
    tax_amount = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
        help_text="Jumlah pajak dari taxes di lines"
    )

    # Tambahan
    
    LETTER_SEA_SI = "SEA_SI"
    LETTER_AIR_SLI = "AIR_SLI"
    LETTER_TRUCK_TO = "TRUCK_TO"

    LETTER_TYPE_CHOICES = [
        (LETTER_SEA_SI, "Shipping Instruction (Sea)"),
        (LETTER_AIR_SLI, "Shipping Letter of Instruction (Air)"),
        (LETTER_TRUCK_TO, "Trucking Order"),
    ]    

      # ==========================
    # Header JSON (DOCUMENT DATA)
    # ==========================
    header_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible header data for SI / SLI / Trucking Order",
    )

    letter_type = models.CharField(
        max_length=20,
        choices=LETTER_TYPE_CHOICES,
        default=LETTER_TRUCK_TO,
        help_text="Jenis dokumen: Sea SI / Air SLI / Trucking Order",
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
       
    last_synced_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_bookings"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking_no or 'DRAFT'} - {self.job_order_id}"
    
    def _get_letter_sequence_code(self):
        lt = (self.letter_type or "").upper()
        if lt in ("SEA_SI", "SI"):
            return "SEA_SI"
        if lt in ("AIR_SLI", "SLI"):
            return "AIR_SLI"
        if lt in ("TRUCK_TO", "SO"):
            return "TRUCK_TO"
        return "WORKING_ORDER"

    
    def recompute_vendor_booking_totals(vb):
    # subtotal
        subtotal = vb.lines.aggregate(s=Sum("amount"))["s"] or Decimal("0")

        # tax total (loop karena tax per line)
        tax_total = Decimal("0")
        for ln in vb.lines.all().prefetch_related("taxes"):
            tax_total += compute_line_tax_amount(ln)
        tax_total = tax_total.quantize(Decimal("0.01"))

        # wht dari header
        wht_rate = Decimal(getattr(vb, "wht_rate", 0) or 0) / Decimal("100")
        # base WHT: biasanya subtotal (tanpa PPN), kalau di bisnis kamu beda tinggal ubah di sini
        wht_amt = (subtotal * wht_rate).quantize(Decimal("0.01"))

        vb.subtotal_amount = subtotal.quantize(Decimal("0.01"))
        vb.tax_amount = tax_total
        vb.wht_amount = wht_amt

        vb.total_amount = (vb.subtotal_amount + vb.tax_amount - vb.wht_amount).quantize(Decimal("0.01"))

        # penting: hindari recursion save() line
        vb.save(update_fields=["subtotal_amount", "tax_amount", "wht_amount", "total_amount"])

    
    def save(self, *args, **kwargs):
        creating = self.pk is None

        # ✅ default issued_date biar tidak invalid
        if not self.issued_date:
            self.issued_date = timezone.now().date()

        # ✅ default discount_amount (kalau field ini required)
        if getattr(self, "discount_amount", None) in (None, ""):
            self.discount_amount = Decimal("0")

        # ✅ pastikan letter_type ada sebelum ambil sequence code
        if not self.letter_type:
            # fallback aman (sesuai desain: TRUCK_TO = SO)
            self.letter_type = "TRUCK_TO"

        if creating:
            # 1️⃣ Nomor finance (VBO) – universal
            if not self.vb_number:
                self.vb_number = get_next_number("shipments", "VENDOR_BOOKING")

            # 2️⃣ Nomor surat vendor – tergantung letter_type
            if not self.letter_number:
                seq_code = self._get_letter_sequence_code()  # SEA_SI / AIR_SLI / TRUCK_TO / WORKING_ORDER
                self.letter_number = get_next_number("shipments", seq_code)

        super().save(*args, **kwargs)

    # ==========================
    # Header helpers
    # ==========================
    def get_header(self, key, default=""):
        return (self.header_json or {}).get(key, default)

    def set_header(self, key, value):
        data = self.header_json or {}
        data[key] = value
        self.header_json = data

    
   
    def job_cost_last_update(self):
        # cari updated_at jobcost terkait booking group & vendor
        from job.models.costs import JobCost

        qs = JobCost.objects.filter(
            job_order_id=self.job_order_id,
            is_active=True,
            cost_type__requires_vendor=True,
            cost_type__cost_group=self.booking_group,
        )
        if self.vendor_id:
            qs = qs.filter(vendor_id=self.vendor_id)

        return qs.aggregate(mx=Max("updated_at"))["mx"]





from decimal import Decimal, ROUND_HALF_UP

Q2 = Decimal("0.01")
def q2(x):
    return Decimal(x or 0).quantize(Q2, rounding=ROUND_HALF_UP)


class VendorBookingLine(models.Model):
    vendor_booking = models.ForeignKey("shipments.VendorBooking", on_delete=CASCADE, related_name="lines")
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


    # ✅ auto description (editable)
    description = models.CharField(max_length=255, blank=True, default="")

    qty = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))

    uom = models.CharField(max_length=20, blank=True, default="")
    
    details = models.JSONField(default=dict, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    cost_group = models.CharField(max_length=50, blank=True, default="")

     # ✅ NEW: FK ke JobCost (source of truth)
    job_cost = models.ForeignKey(
        "job.JobCost",
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_index=True,
        help_text="Source Job Cost line (for allocation & locking).",
    )

    # ✅ keep cost_type (denormalisasi + untuk query/report cepat)
    cost_type = models.ForeignKey(
        "job.JobCostType",
        on_delete=PROTECT,
        related_name="+",
    )


    
    taxes = models.ManyToManyField(Tax, blank=True, related_name="booking_lines")
    vat_included = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vendor_booking_lines"
        ordering = ["vendor_booking_id", "line_no"]


    def compute_line_tax_amount(line) -> Decimal:
        """
        Hitung total pajak add-on dari line.taxes.
        Asumsi Tax punya field: rate (persen).
        Kalau Tax kamu beda, tinggal mapping di sini.
        """
        base = Decimal(line.amount or 0)
        total = Decimal("0")

        # M2M case
        for t in line.taxes.all():
            rate = Decimal(getattr(t, "rate", 0) or 0) / Decimal("100")
            total += (base * rate)

        return total.quantize(Decimal("0.01"))

    def recompute_amount(self):
        q = Decimal(self.qty or 0)
        p = Decimal(self.unit_price or 0)
        self.amount = (q * p).quantize(Decimal("0.01"))

    
    def clean(self):
        # ✅ job_cost wajib untuk line vendor booking (karena base on job cost)
        if not self.job_cost_id:
            raise ValidationError("Job Cost wajib dipilih (Vendor Booking Line harus berasal dari Job Cost).")

        # ✅ hard-consistency: vendor booking job_order harus sama dengan job_cost.job_order
        if self.vendor_booking_id and self.job_cost_id:
            if self.job_cost.job_order_id != self.vendor_booking.job_order_id:
                raise ValidationError("Job Cost tidak sesuai Job Order Vendor Booking.")

        # ✅ hard-consistency: vendor booking vendor harus sama dengan job_cost.vendor
        if self.vendor_booking_id and self.job_cost_id:
            if self.job_cost.vendor_id and self.vendor_booking.vendor_id:
                if self.job_cost.vendor_id != self.vendor_booking.vendor_id:
                    raise ValidationError("Vendor pada Job Cost tidak sesuai Vendor Booking.")

    
   
    def _get_uom_code_from_jobcost(jc: JobCost) -> str:
        if jc.cost_type_id and getattr(jc, "cost_type", None) and getattr(jc.cost_type, "uom", None):
            return jc.cost_type.uom.code
        return ""


    def save(self, *args, **kwargs):
        # ✅ auto-sync cost_type dari job_cost (source of truth)
        if self.job_cost_id:
            self.cost_type_id = self.job_cost.cost_type_id
            if not self.description:
                self.description = self.job_cost.description or str(self.job_cost.cost_type)

        # ✅ auto calc amount
        if self.unit_price is not None and self.qty is not None:
            self.amount = (self.qty or 0) * (self.unit_price or 0)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor_booking_id} - {self.job_cost_id}"

    def base_amount(self) -> Decimal:
        return q2(self.amount)

    def tax_amount(self) -> Decimal:
        base = self.base_amount()
        total = Decimal("0")
        for t in self.taxes.all():
            rate = Decimal(getattr(t, "rate", 0) or 0) / Decimal("100")
            total += base * rate
        return q2(total)

    def line_total(self) -> Decimal:
        return q2(self.base_amount() + self.tax_amount())
