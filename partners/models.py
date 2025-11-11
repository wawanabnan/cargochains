from django.conf import settings
from django.db import models
from django.utils import timezone


class Partner(models.Model):
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
    websites =  models.CharField(max_length=30, null=True, blank=True)
    company_name = models.CharField(
        max_length=100,
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
    is_individual = models.BooleanField(default=False, help_text="Centang jika perorangan; kosongkan jika perusahaan.")
    is_pkp = models.BooleanField(default=False, help_text="Centang jika PKP (Pengusaha Kena Pajak).")

    tax = models.CharField(max_length=50,   null=True, blank=True)   # NPWP / Tax ID
    address = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100,   null=True, blank=True)
    post_code = models.CharField(max_length=20, null=True, blank=True)
    
    
    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="partners",
        db_index=True,
        null=True, blank=True,
        db_column="sales_user_id",
        help_text="PIC sales/AM yang bertanggung jawab."
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partners"
        indexes = [models.Index(fields=["name"], name="partners_name_idx")]

    def __str__(self): return self.name
    #def __str__(self): 
    #    return f"{self.partner.name} → {self.role_type}"  # bukan self.role


class PartnerRoleTypes(models.Model):
    code = models.CharField(max_length=50, unique=True,blank=True);
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "partner_role_types"
        verbose_name = "Partner Role Types"
        verbose_name_plural = "Partner Roles Type"
        ordering = ["name"]

    def __str__(self):
        return self.name




class PartnerRole(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="partner_roles")
    role_type = models.ForeignKey(PartnerRoleTypes, on_delete=models.CASCADE, related_name="partner_roles")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_roles"
        unique_together = ("partner", "role_type")
        verbose_name = "Partner Role"
        verbose_name_plural = "Partner Roles"

    def __str__(self): return f"{self.partner.name} → {self.role}"
    
    @property
    def role(self):
        return self.role_type
    
    def roles_display(self, obj):
        qs = (PartnerRole.objects
          .filter(partner=obj)
          .select_related("role_type")
          .values_list("role_type__name", flat=True))
        names = sorted(set(qs))
        return ", ".join(names) if names else "-"


