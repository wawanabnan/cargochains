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
    
    def _get_letter_sequence_code(self) -> str:
        """
        Mapping letter_type -> NumberSequence.code
        """
        if self.letter_type == self.LETTER_SEA_SI:
            return "SEA_SI"
        if self.letter_type == self.LETTER_AIR_SLI:
            return "AIR_SLI"
        return "WORKING_ORDER"

    # ==========================
    # Save override (numbering)
    # ==========================
    def save(self, *args, **kwargs):
        # 1️⃣ Nomor finance (VBO) – universal
        if not self.pk and not self.vb_number:
            # app = 'shipments', code = 'VENDOR_BOOKING'
            self.vb_number = get_next_number("shipments", "VENDOR_BOOKING")

        # 2️⃣ Nomor surat vendor – tergantung letter_type
        if not self.pk and not self.letter_number:
            seq_code = self._get_letter_sequence_code()
            # contoh:
            # app = 'shipments', code = 'SEA_SI' / 'AIR_SLI' / 'TRUCK_TO'
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

    
    from django.db.models import Max

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vendor_booking_lines"
        ordering = ["vendor_booking_id", "line_no"]

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
        return f"{self.vendor_booking_id} - {self.cost_type}"
