from django.conf import settings
from django.db import models
from django.utils import timezone


class TaxCategory(models.Model):
    code = models.CharField(max_length=20, unique=True)   # PPN, PPH
    name = models.CharField(max_length=50)                # Pajak Pertambahan Nilai, Pajak Penghasilan
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Tax(models.Model):
    category = models.ForeignKey(TaxCategory, on_delete=models.PROTECT, related_name="taxes")
    name = models.CharField(max_length=80)  # PPN 11%, PPN Barang Mewah, dll
    code = models.CharField(max_length=30, unique=True)     
    rate = models.DecimalField(max_digits=6, decimal_places=2)  # 11.00 / 10.00 / 20.00
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__code", "name"]

    def __str__(self):
         r = str(self.rate or 0).replace(".", ",")
         return f"{r}%"

    
   