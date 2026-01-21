from django.db import models
from decimal import Decimal

from accounting.models.chart  import Account  # <-- sesuaikan path Account model


class TaxCategory(models.Model):
    code = models.CharField(max_length=20, unique=True)   # PPN, PPH
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Tax(models.Model):
    USAGE_SALES = "sales"
    USAGE_PURCHASE = "purchase"
    USAGE_BOTH = "both"
    USAGE_CHOICES = [
        (USAGE_SALES, "Sales"),
        (USAGE_PURCHASE, "Purchase"),
        (USAGE_BOTH, "Sales & Purchase"),
    ]

    category = models.ForeignKey(TaxCategory, on_delete=models.PROTECT, related_name="taxes")
    name = models.CharField(max_length=80)                 # PPN 11%, PPH 23, dll
    code = models.CharField(max_length=30, unique=True)
    rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    usage = models.CharField(max_length=10, choices=USAGE_CHOICES, default=USAGE_SALES)

    # --- accounting mapping ---
    output_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Account untuk pajak keluaran (Sales Tax Payable)."
    )
    input_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Account untuk pajak masukan (Purchase Tax Receivable)."
    )

    # withholding (PPH) flag (optional, future proof)
    is_withholding = models.BooleanField(
        default=False,
        help_text="Centang jika tax ini withholding (mis: PPh)."
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__code", "name"]

    def __str__(self):
        r = self.rate or 0
        # rapihin trailing .0
        if float(r).is_integer():
            return f"{int(r)}%"
        return f"{r}%"
