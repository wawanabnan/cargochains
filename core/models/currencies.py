from django.conf import settings
from django.db import models
from django.utils import timezone


class Currency(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # contoh: IDR, USD
    symbol = models.CharField(max_length=8, blank=True, null=True)
    decimals = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "currencies"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}"

