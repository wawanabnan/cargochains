from django.conf import settings
from django.db import models
from django.utils import timezone

# core/models.py
from django.db import models
        


class UOM(models.Model):
    code = models.CharField(max_length=20, unique=True)  # e.g. KG, CBM, PKG
    name = models.CharField(max_length=100)              # e.g. Kilogram, Cubic Meter
    category = models.CharField(max_length=50, blank=True, null=True)  # Weight/Volume/Count (opsional)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "uoms"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name}"
    
        

                    
