from django.conf import settings
from django.db import models
from django.utils import timezone

# core/models.py
from django.db import models
from accounting.models.chart import Account
from django.db.models import PROTECT


class CompanyProfile(models.Model):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    address_1 = models.CharField(max_length=255, blank=True,null=True)
    address_2 = models.CharField(max_length=255, blank=True, null=True)

    country  = models.ForeignKey("geo.Location", on_delete=PROTECT, related_name="+",default=1)
    province = models.ForeignKey("geo.Location", on_delete=PROTECT, related_name="+", blank=True, null=True)
    regency  = models.ForeignKey("geo.Location", on_delete=PROTECT, related_name="+", blank=True, null=True)
    district = models.ForeignKey("geo.Location", on_delete=PROTECT, related_name="+", blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)

    enable_job_cost = models.BooleanField(default=True)
    enable_auto_journal = models.BooleanField(default=False)


    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    is_default = models.BooleanField(default=False)
    npwp = models.CharField(max_length=50, blank=True, null=True)
    is_pkp = models.BooleanField(default=False)
    footer_text = models.TextField(blank=True, null=True)
    enable_multi_currency = models.BooleanField(default=False)
    enable_tax = models.BooleanField(default=True)
    default_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "core_company_profiles"

    def __str__(self):
        return self.brand or self.name
    
from django.core.exceptions import ValidationError

def clean(self):
    if self.province and self.province.kind != "province":
        raise ValidationError({"province": "Province must be kind=province"})
    if self.regency and self.regency.kind not in ("regency", "city"):
        raise ValidationError({"regency": "Regency must be kind=regency/city"})
    if self.district and self.district.kind != "district":
        raise ValidationError({"district": "District must be kind=district"})

    # parent check (kalau data Location pakai parent)
    if self.regency and self.province and self.regency.parent_id != self.province_id:
        raise ValidationError({"regency": "Regency must be under selected province"})
    if self.district and self.regency and self.district.parent_id != self.regency_id:
        raise ValidationError({"district": "District must be under selected regency"})

