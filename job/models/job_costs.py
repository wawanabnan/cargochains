from django.db import models
from django.db.models.deletion import PROTECT

from accounting.models.chart import Account
from partners.models import Vendor
from job.models.job_orders import JobOrder
from core.models.currencies import Currency
from decimal import Decimal
from core.models.taxes import Tax

from django.db import models
from django.db.models import PROTECT
from job.constants import SYSTEM_GROUP_CHOICES, CostGroup
from django.core.validators import MinValueValidator
from core.models.uoms import UOM


class JobCostType(models.Model):
       
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=120)

    # ✅ jadi terstruktur biar gampang mapping UI
    cost_group = models.CharField(
        max_length=50,
        blank=True,
        choices=SYSTEM_GROUP_CHOICES,
    )
    
    uom = models.ForeignKey(
        UOM,
        related_name="cost_line_uoms",
        on_delete=PROTECT,
        null=True,
        blank=True,
        help_text="Default UOM untuk cost line (mis: LS, TRIP, CNTR, CBM, KG)"
    )

    taxes = models.ManyToManyField(Tax, blank=True, related_name="cost_lines_taxes")

    # ✅ sumber kebenaran UX: vendor vs non-vendor
    requires_vendor = models.BooleanField(default=True)

    # ✅ akun debit COGS untuk accrual saat Job Completed
    cogs_account = models.ForeignKey(
        "accounting.Account",  # sesuaikan import/path Account om
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="COGS account (debit) untuk accrual saat Job Completed",
    )

    # ✅ akun credit (liability/AP) pasangan COGS untuk accrual
    accrued_liability_account = models.ForeignKey(
        "accounting.Account",  # sesuaikan import/path Account om
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Liability/AP account (credit) untuk accrual saat Job Completed",
    )

    # ✅ default schema modal (operasional)
    service_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="Default schema modal untuk booking line",
    )

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_cost_types"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name}"
    
    def clean(self):
        super().clean()
        # ✅ aturan inti: service_type selalu mirror cost_group
        self.service_type = self.cost_group or self.Group.OTHER

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)



class JobCost(models.Model):

    job_order = models.ForeignKey(
        "job.JobOrder",
        on_delete=PROTECT,
        related_name="job_costs",
    )

    cost_type = models.ForeignKey(
        "job.JobCostType",
        on_delete=PROTECT,
        related_name="job_cost_types",
    )

    description = models.CharField(max_length=255, blank=False, default="")

    qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Quantity"
    )

    price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Unit price (foreign or local)"
    )

    currency = models.ForeignKey(
        "core.Currency",
        on_delete=PROTECT,
        null=True,
        blank=True,
        help_text="Currency of price"
    )

    rate = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=1,
        help_text="Currency rate to Job currency (IDR)"
    )
   
    tax = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Estimated amount (system or manual)"
    )
    est_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Estimated amount (system or manual)"
    )

    actual_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Actual amount (after vendor invoice)"
    )

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # ==========================================================
    # ✅ VENDOR (SUDAH ADA, DIPERTAHANKAN)
    # ==========================================================
    vendor = models.ForeignKey(
        "partners.Vendor",
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_index=True,
    )

    internal_note = models.CharField(max_length=120, blank=True)

    # ==========================================================
    # ✅ VENDOR BOOKING TRACKING (BARU)
    # ==========================================================
    vb_allocated_qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total qty already allocated to Vendor Booking"
    )

    VB_NONE = "NONE"
    VB_PARTIAL = "PARTIAL"
    VB_FULL = "FULL"

    vb_status = models.CharField(
        max_length=10,
        choices=[
            (VB_NONE, "Not Booked"),
            (VB_PARTIAL, "Partially Booked"),
            (VB_FULL, "Fully Booked"),
        ],
        default=VB_NONE,
        db_index=True,
        help_text="Vendor Booking allocation status"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_costs"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Job#{self.job_order_id} - {self.cost_type}"

    # ==========================================================
    # DERIVED / HELPERS
    # ==========================================================
    @property
    def amount(self):
        """
        qty × price × rate
        (dipertahankan untuk backward compatibility)
        """
        return (self.qty or 0) * (self.price or 0) * (self.rate or Decimal("1"))

    @property
    def vb_open_qty(self):
        """
        Remaining qty that can still be booked to vendor
        """
        return max((self.qty or 0) - (self.vb_allocated_qty or 0), Decimal("0"))

    @property
    def is_vb_open(self):
        """
        Convenience flag for UI / filtering
        """
        return self.vb_status != self.VB_FULL
    
   