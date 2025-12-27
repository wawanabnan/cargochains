from django.db import models
from django.db.models import Q

from core.models.taxes import Tax


class SalesTaxPolicy(models.Model):
    """Control which taxes are available per Sales module (Invoice, SO, Quotation, etc.)."""

    MODULE_INVOICE = "INVOICE"
    MODULE_SO = "SO"
    MODULE_QUOTATION = "QUOTATION"

    MODULE_CHOICES = [
        (MODULE_INVOICE, "Invoice"),
        (MODULE_SO, "Sales Order"),
        (MODULE_QUOTATION, "Quotation"),
    ]

    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    tax = models.ForeignKey(Tax, on_delete=models.PROTECT, related_name="sales_policies")
    is_active = models.BooleanField(default=True)

    # Optional: one default per module
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ("module", "tax")
        ordering = ["module", "tax__name"]

    def __str__(self) -> str:
        return f"{self.module} - {self.tax.code}"

    def save(self, *args, **kwargs):
        # enforce only one default tax per module
        super().save(*args, **kwargs)
        if self.is_default:
            SalesTaxPolicy.objects.filter(
                module=self.module
            ).exclude(pk=self.pk).update(is_default=False)
