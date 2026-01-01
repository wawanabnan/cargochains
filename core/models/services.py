from django.conf import settings
from django.db import models
from django.utils import timezone

# core/models.py
from django.db import models
from accounting.models.chart import Account
from django.db.models import PROTECT

class Service(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100)
    service_group = models.CharField(max_length=30)
    revenue_account = models.ForeignKey(
        Account,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    receivable_account = models.ForeignKey(
        Account,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_services"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} - {self.service_group}"



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
    
    @property
    def is_door_to_door(self) -> bool:
        """
        Return True jika service adalah Door to Door,
        berdasarkan prefix kode: D2D_...
        """
        return self.code.startswith("D2D_")

    @property
    def is_door_to_port(self) -> bool:
        """
        True jika layanan Door to Port, contoh kode:
        D2P_SEA, D2P_AIR, dll.
        """
        return self.code.upper().startswith("D2P_")

    @property
    def is_port_to_door(self) -> bool:
        """
        True jika layanan Port to Door, contoh kode:
        P2D_SEA, P2D_AIR, dll. (kalau nanti om pakai prefix ini)
        """
        return self.code.upper().startswith("P2D_")

    @property
    def is_port_to_port(self) -> bool:
        """
        True jika layanan Port to Port, contoh kode:
        P2P_SEA, P2P_AIR, dll.
        """
        return self.code.upper().startswith("P2P_")

    @property
    def service_mode(self) -> str:
        """
        Ringkasan mode service: 'D2D', 'D2P', 'P2D', 'P2P', atau 'OTHER'
        Bisa dipakai di template / UI untuk badge/color.
        """
        code = self.code.upper()
        if code.startswith("D2D_"):
            return "D2D"
        if code.startswith("D2P_"):
            return "D2P"
        if code.startswith("P2D_"):
            return "P2D"
        if code.startswith("P2P_"):
            return "P2P"
        return "OTHER"