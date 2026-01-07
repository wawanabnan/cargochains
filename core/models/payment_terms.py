from django.conf import settings
from django.db import models
from django.utils import timezone

class PaymentTerm(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    days = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True, null=True)

    dp_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Down Payment (%) misal 20.00. Kosongkan jika tidak ada DP."
    )

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        db_table = "payment_terms"
        ordering = ["name"]

    def __str__(self):
        return self.name
