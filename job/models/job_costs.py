from django.db import models
from django.db.models.deletion import PROTECT

from accounting.models.chart import Account
from partners.models import Vendor
from job.models.job_orders import JobOrder

class JobCostType(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=120)

    # ✅ ganti "group" (keyword SQL) -> cost_group
    cost_group = models.CharField(max_length=50, blank=True, default="")

    # ✅ sumber kebenaran untuk UX: vendor vs non-vendor
    requires_vendor = models.BooleanField(default=True)

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_cost_types"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name}"



class JobCost(models.Model):
  
    job_order = models.ForeignKey(JobOrder, on_delete=PROTECT, related_name="job_order_costs")
    cost_type = models.ForeignKey(JobCostType, on_delete=PROTECT, related_name="+")
    description = models.CharField(max_length=255, blank=True, default="")
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
