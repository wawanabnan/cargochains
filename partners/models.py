from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class Partner(TimeStampedModel):
    COMPANY_TYPE_CHOICES = [
        ('PT', 'PT'),
        ('CV', 'CV'),
        ('UD', 'UD'),
        ('UKM', 'UKM'),
    ]
    name = models.CharField(max_length=120)
    email = models.CharField(max_length=120, null=True, blank=True)
    phone = models.CharField(max_length=60,  null=True, blank=True)
    mobile = models.CharField(max_length=30, null=True, blank=True)
    websites = models.JSONField(null=True, blank=True, help_text="Daftar URL (list of strings). Kosongkan jika tidak ada.")
    company_name = models.CharField(
        max_length=255,
        verbose_name="Company Name",
        blank=True,
        null=True
    )
    company_type = models.CharField(
        max_length=10,
        choices=COMPANY_TYPE_CHOICES,
        verbose_name="Company Type",
        blank=True,
        null=True
    )

    tax = models.CharField(max_length=50,   null=True, blank=True)   # NPWP / Tax ID
    address = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100,   null=True, blank=True)
    postcode = models.CharField(max_length=20, null=True, blank=True)

    is_individual = models.BooleanField(default=False, help_text="Centang jika perorangan; kosongkan jika perusahaan.")
    
    is_pkp = models.BooleanField(default=False, help_text="Centang jika PKP (Pengusaha Kena Pajak).")

    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="partners",
        db_index=True,
        null=True, blank=True,
        db_column="sales_user_id",
        help_text="PIC sales/AM yang bertanggung jawab."
    )



    class Meta:
        db_table = "partners"
        indexes = [models.Index(fields=["name"], name="partners_name_idx")]

    def __str__(self): return self.name

class PartnerRole(TimeStampedModel):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, db_column="partner_id", related_name="roles")
    role = models.CharField(max_length=30)  # 'customer','agency','vendor','carrier',...

    class Meta:
        db_table = "partner_roles"
        unique_together = (("partner", "role"),)
        indexes = [models.Index(fields=["partner", "role"], name="partner_role_idx")]

    def __str__(self): return f"{self.partner.name} → {self.role}"
