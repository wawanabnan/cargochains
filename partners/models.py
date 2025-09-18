from django.db import models
from core.models import TimeStampedModel

class Partner(TimeStampedModel):
    name = models.CharField(max_length=120)
    email = models.CharField(max_length=120, null=True, blank=True)
    phone = models.CharField(max_length=60,  null=True, blank=True)
    tax = models.CharField(max_length=50,   null=True, blank=True)   # NPWP / Tax ID
    address = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100,   null=True, blank=True)
    postcode = models.CharField(max_length=20, null=True, blank=True)

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
