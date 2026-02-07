# sales/models.py
from django.db import models
from django.db.models import PROTECT, CASCADE, F, Sum
from partners.models import Partner
from geo.models import Location
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from core.models.services import SalesService 
from core.models.uoms import UOM     
from core.models.payment_terms import PaymentTerm
from core.models.currencies import Currency
from sales.invoice_model import *
from sales.job_order_model import *
from sales.config_model import *


class SalesQuotation(models.Model):
    STATUS_DRAFT     = "DRAFT"
    STATUS_SENT      = "SENT"
    STATUS_ACCEPTED  = "ACCEPTED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_EXPIRED   = "EXPIRED"
    STATUS_ORDERED   = "ORDERED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_ORDERED, "Ordered"), 
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    
    # Transisi yang diizinkan:
    # DRAFT -> SENT
    # SENT -> {ACCEPTED, CANCELLED, EXPIRED}
    # ACCEPTED -> {CANCELLED}  (opsional; hapus jika tak diinginkan)
    # CANCELLED -> {} (final)
    # EXPIRED -> {} (final)

    _ALLOWED_TRANSITIONS = {
        STATUS_DRAFT:    {STATUS_SENT},
        STATUS_SENT:     {STATUS_ACCEPTED, STATUS_CANCELLED},  # (EXPIRED kalau mau otomatis)
        STATUS_ACCEPTED: set(),
        STATUS_ACCEPTED: {STATUS_ORDERED},  
        STATUS_CANCELLED:set(),
        STATUS_EXPIRED:  set(),
    }

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self._ALLOWED_TRANSITIONS.get(self.status, set())

    # (opsional) buat nentuin warna badge di template
    def status_badge_class(self) -> str:
        return {
            self.STATUS_DRAFT: "bg-secondary",
            self.STATUS_SENT: "bg-info",
            self.STATUS_ACCEPTED: "bg-success",
            self.STATUS_CANCELLED: "bg-danger",
            self.STATUS_EXPIRED: "bg-warning",
            self.STATUS_ORDERED: "bg-primary",
            
        }.get(self.status, "bg-secondary")

    number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Partner, on_delete=PROTECT, related_name="quotations")
    date = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=False)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))

    total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))         # subtotal
    vat = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))           # pajak (amount)
    grand_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))   # total + vat


    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales_quotations",
        db_index=True,
        null=True, blank=True,
        db_column="sales_user_id",
    )
    # relasi service by code (kolom DB varchar via db_column)
    sales_service = models.ForeignKey(
        SalesService,
        db_column="sales_service_id",
        on_delete=PROTECT,
        related_name="quotations",
    )

    # FK standar ke currencies.id (kolom DB = currency_id INTEGER)
    currency = models.ForeignKey(
        Currency, on_delete=PROTECT, related_name="quotations", null=False ,blank=False)

    payment_term = models.ForeignKey(
        PaymentTerm, on_delete=PROTECT, related_name="quotations", null=True, blank=False
    )

    # notes sesuai permintaan
    note_1 = models.TextField(blank=True, null=True)
    note_2 = models.TextField(blank=True, null=True)

    amount_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    business_type = models.CharField(max_length=20, default="freight")

    # info sales
    sales_agency = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name="agency_quotations"
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_quotations"


    def recalc_totals(self):
        """
        Hitung subtotal dari lines, kemudian grand_total = total + vat.
        total_amount (legacy) ikut diset = total agar kompatibel.
        """
        subtotal = (self.lines
                    .annotate(line_total=F("qty") * F("price"))
                    .aggregate(s=Sum("line_total"))["s"] or Decimal("0.00"))
        self.total = subtotal
        # pastikan vat tidak None
        self.vat = self.vat or Decimal("0.00")
        self.grand_total = self.total + self.vat

        # sinkron ke legacy field (sementara)
        self.total_amount = self.total

        self.save(update_fields=["total", "vat", "grand_total", "total_amount"])
        return self.grand_total
    

    def __str__(self):
        return self.number


class SalesQuotationLine(models.Model):
    sales_quotation = models.ForeignKey(SalesQuotation, on_delete=CASCADE, related_name="lines")
    origin = models.ForeignKey(Location, on_delete=PROTECT, related_name="quotation_origin_lines")
    destination = models.ForeignKey(Location, on_delete=PROTECT, related_name="quotation_destination_lines")
    description = models.CharField(max_length=200, blank=True, null=True)
    uom = models.ForeignKey(UOM, on_delete=PROTECT)
    qty = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_quotation_lines"

    def __str__(self):
        return f"{self.description or ''} ({self.qty} {self.uom})"


class SalesOrder(models.Model):
    number = models.CharField(max_length=50, unique=True)
    ref_number= models.CharField(max_length=20, blank=True, null=True)

    sales_quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        db_column="sales_quotation_id",
    )
    
    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales_orders",
        db_index=True,
        null=True, blank=True,
        db_column="sales_user_id",
    )
   
    sales_service = models.ForeignKey(   # ✅ field baru
        SalesService,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders"
    )


    customer = models.ForeignKey(Partner, on_delete=PROTECT, related_name="orders")
    date = models.DateField(null=True, blank=True)

    currency = models.ForeignKey(Currency, on_delete=PROTECT, related_name="orders")
    payment_term = models.ForeignKey(
        PaymentTerm, on_delete=PROTECT, related_name="orders", null=True, blank=True
    )

    # order tidak pakai valid_until
    notes = models.TextField(blank=True, null=True)
    # === TOTALS BARU ===
    total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))         # subtotal
    vat = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))           # pajak (amount)
    grand_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))   # total + vat

    project = models.OneToOneField(
        "projects.Project", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sales_order"
    )
    
    # --- STATUS constants ---
    STATUS_DRAFT     = "DRAFT"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_PROGRESS  = "ON_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_HOLD      = "ON_HOLD"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_PROGRESS, "On Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_HOLD, "On Hold"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    # --- allowed transitions ---
    _ALLOWED_TRANSITIONS = {
        STATUS_DRAFT:     {STATUS_CONFIRMED, STATUS_CANCELLED},
        STATUS_CONFIRMED: {STATUS_PROGRESS, STATUS_CANCELLED, STATUS_HOLD},
        STATUS_PROGRESS:  {STATUS_COMPLETED, STATUS_CANCELLED, STATUS_HOLD},
        STATUS_HOLD:      {STATUS_PROGRESS, STATUS_CANCELLED},
        STATUS_COMPLETED: set(),
        STATUS_CANCELLED: set(),
    }

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self._ALLOWED_TRANSITIONS.get(self.status, set())

    # ... fields: number, sales_quotation, customer, total, vat, grand_total, business_type ...

    
    business_type = models.CharField(max_length=20, default="freight")
    

    # info sales
    sales_agency = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name="agency_orders"
    )
    # sales_reseller: DIHAPUS

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_orders"
       
    @property
    def sales_user_name(self):
        user = self.sales_user
        return user.get_full_name() or user.username    

    def __str__(self):
        return self.number

class SalesModule(SalesOrder):
    class Meta:
        proxy = True                   # ✅ hanya proxy
        app_label = "sales"
        verbose_name = "Sales module"
        verbose_name_plural = "Sales module"
        permissions = (
            ("access_sales", "Can access Sales module"),
            ("view_all_sales", "Can view all sales data"),  # ← IZIN KUNCI
        )

        
class SalesOrderLine(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=CASCADE, related_name="lines")

    origin = models.ForeignKey(Location, on_delete=PROTECT, related_name="order_origin_lines")
    destination = models.ForeignKey(Location, on_delete=PROTECT, related_name="order_destination_lines")
    description = models.CharField(max_length=200, blank=True, null=True)
    uom = models.ForeignKey(UOM, on_delete=PROTECT)
    qty = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

   
    class Meta:
        db_table = "sales_order_lines"

    def __str__(self):
        return f"{self.description or ''} ({self.qty} {self.uom})"

