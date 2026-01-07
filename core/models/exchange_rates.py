# core/models/exchange_rates.py
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class ExchangeRate(models.Model):
    currency = models.ForeignKey("core.Currency", on_delete=models.PROTECT, related_name="+")
    rate_date = models.DateField(db_index=True)
    rate_to_idr = models.DecimalField(
        max_digits=18, decimal_places=6,
        validators=[MinValueValidator(Decimal("0.000001"))]
    )
    source = models.CharField(max_length=50, blank=True, default="MANUAL")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["rate_date", "currency"], name="uq_rate_date_currency")
        ]   
        db_table = "core_exchange_rates"
        indexes = [
            models.Index(fields=["currency", "rate_date"]),
        ]
        unique_together = [("currency", "rate_date")]

    def __str__(self):
        return f"{self.currency.code} {self.rate_date} = {self.rate_to_idr}"
