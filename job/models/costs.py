from django.db import models
from django.db.models.deletion import PROTECT

from accounting.models.chart import Account
from partners.models import Vendor
from job.models.job_orders import JobOrder
from core.models.currencies import Currency
from decimal import Decimal


from django.db import models
from django.db.models import PROTECT

class JobCostType(models.Model):
    class CostGroup(models.TextChoices):
        TRANSPORT = "TRANSPORT", "Transport"
        PORT = "PORT", "Port & Terminal"
        PACKING = "PACKING", "Packing"
        DOCUMENT = "DOCUMENT", "Documentation"
        WAREHOUSE = "WAREHOUSE", "Warehouse"
        OTHER = "OTHER", "Other"

    class ServiceType(models.TextChoices):
        TRUCK = "TRUCK", "Trucking"
        SEA = "SEA", "Sea"
        AIR = "AIR", "Air"
        PACKING = "PACKING", "Packing"
        DOCUMENT = "DOCUMENT", "Documentation"
        OTHER = "OTHER", "Other"

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=120)

    # ✅ jadi terstruktur biar gampang mapping UI
    cost_group = models.CharField(
        max_length=50,
        blank=True,
        default=CostGroup.OTHER,
        choices=CostGroup.choices,
    )

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
        choices=ServiceType.choices,
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


from job.models.costs import JobCostType
class JobCost(models.Model):
  
    job_order = models.ForeignKey("job.JobOrder", on_delete=PROTECT, related_name="job_costs")
    cost_type = models.ForeignKey(JobCostType, on_delete=PROTECT, related_name="job_cost_types")
    description = models.CharField(max_length=255, blank=False, default="")
    
    qty = models.DecimalField(
        max_digits=12, decimal_places=2, default=1,
        help_text="Quantity"
    )
    price = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Unit price (foreign or local)"
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Currency of price"
    )

    rate = models.DecimalField(
        max_digits=18, decimal_places=6,
        default=1,
        help_text="Currency rate to Job currency (IDR)"
    )

    est_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    actual_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Category(models.TextChoices):
        VENDOR = "VENDOR", "Vendor Cost"
        MOBILIZATION = "MOBILIZATION", "Mobilization"
        LABOUR = "LABOUR", "Labour"
        DOCUMENT = "DOCUMENT", "Document"
        MISC = "MISC", "Misc"

   
    # ✅ tambahan
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.VENDOR,
        db_index=True,
    )

    # ✅ tambahan (boleh kosong)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_index=True,
    )
    internal_note = models.CharField(max_length=120, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_costs"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Job#{self.job_id} - {self.cost_type}"

    @property
    def amount(self):
        """
        qty × price × rate
        """
        return (self.qty or 0) * (self.price or 0) * (self.rate or Decimal("1"))