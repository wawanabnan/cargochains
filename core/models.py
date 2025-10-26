from django.conf import settings
from django.db import models
from django.utils import timezone

# core/models.py
from django.db import models

class NumberSequence(models.Model):
    RESET_NONE = "none"
    RESET_MONTHLY = "monthly"
    RESET_YEARLY = "yearly"
    RESET_CHOICES = [
        (RESET_NONE, "None"),
        (RESET_MONTHLY, "Monthly"),
        (RESET_YEARLY, "Yearly"),
    ]

    app_label   = models.CharField(max_length=50)                   # "sales", "shipments", dst.
    code        = models.CharField(max_length=50)                   # "FREIGHT_QUOTATION", "FREIGHT_ORDER", dll.
    name = models.CharField(max_length=100, null=True, blank=True)  # sementara

    prefix      = models.CharField(max_length=20, blank=True, default="")  # "FQ", "SO", dll.
    format      = models.CharField(                                   # Template fleksibel
        max_length=120,
        default="{prefix}{year:04d}{month:02d}-{seq:05d}",
        help_text="Gunakan var: prefix, year, month, day (opsional), seq",
    )
    padding     = models.PositiveSmallIntegerField(default=5)        # fallback kalau format pakai {seq:0Nd}

    reset       = models.CharField(max_length=10, choices=RESET_CHOICES, default=RESET_MONTHLY)

    # State periode & counter terakhir
    last_number = models.PositiveIntegerField(default=0)
    period_year = models.PositiveSmallIntegerField(null=True, blank=True)
    period_month= models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "core_number_sequences" 
        constraints = [
            models.UniqueConstraint(fields=["app_label", "code"], name="uniq_sequence_per_app_code"),
        ]
        indexes = [
            models.Index(fields=["app_label", "code"]),
        ]

    def __str__(self):
        return f"{self.app_label}/{self.code} → {self.prefix} (reset={self.reset})"


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
    
        
class SalesService(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

   
    class Meta:
        db_table = "sales_services"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def only_name(self):
        return self.name
                    
class PaymentTerm(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    days = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        db_table = "payment_terms"
        ordering = ["name"]

    def __str__(self):
        return self.name


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

class CoreSetting(models.Model):
    code = models.CharField(max_length=100, unique=True)
    int_value = models.IntegerField(null=True, blank=True)
    char_value = models.CharField(max_length=255, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "core_settings"

    def __str__(self):
        return f"{self.code}"
    

# core/models.py
class CompanyProfile(models.Model):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True, default="")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "core_company_profiles"

    def __str__(self):
        return self.brand or self.name
