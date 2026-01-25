from __future__ import annotations

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class JobFeePeriodStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    APPROVED = "APPROVED", "Approved"
    PAID = "PAID", "Paid"


class JobFeePeriod(models.Model):
    """
    Header payout per bulan.
    Satu period per bulan. Bisa di-regenerate (replace) kalau masih DRAFT.
    """
    month = models.DateField(help_text="Pakai tanggal 1 setiap bulan (YYYY-MM-01).", unique=True)

    percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=16, choices=JobFeePeriodStatus.choices, default=JobFeePeriodStatus.DRAFT)

    total_base_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    total_fee_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))

    generated_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="generated_fee_periods"
    )

    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("-month",)

    def __str__(self) -> str:
        return f"Sales Fee {self.month:%Y-%m} ({self.status})"

    def recalc_totals(self) -> None:
        agg = self.lines.aggregate(
            base=Sum("base_amount"),
            fee=Sum("fee_amount"),
        )
        self.total_base_amount = agg["base"] or Decimal("0.00")
        self.total_fee_amount = agg["fee"] or Decimal("0.00")


class JobFeeLine(models.Model):
    """
    Detail fee per JobOrder complete.
    Snapshot: base_amount + percent + fee_amount
    """
    period = models.ForeignKey(JobFeePeriod, on_delete=models.CASCADE, related_name="lines")

    # Ganti import path ke model JobOrder om
    job_order = models.OneToOneField(
        "job.JobOrder",  # <-- sesuaikan app_label.ModelName
        on_delete=models.PROTECT,
        related_name="sales_fee_line",
    )

    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales_fee_lines"
    )

    base_amount = models.DecimalField(max_digits=18, decimal_places=2)
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=18, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sales_user", "job_order")

    def __str__(self) -> str:
        return f"{self.period.month:%Y-%m} - {self.sales_user} - {self.job_order_id}"
