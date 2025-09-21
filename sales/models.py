# sales/models.py
from django.db import models
from django.db.models import PROTECT, CASCADE, F, Sum
from partners.models import Partner
from geo.models import Location
from decimal import Decimal
from django.utils import timezone

class TimestampedModel(models.Model):
    """Abstract base with created_at & updated_at, safe for fixtures."""
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now, editable=False, db_index=True),
    updated_at = models.DateTimeField(null=True, blank=True, default=timezone.now)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)

class Currency(TimestampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # contoh: IDR, USD
    symbol = models.CharField(max_length=8, blank=True, null=True)
    decimals = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "currencies"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}"


class SalesService(TimestampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # timestamps (PALING BELAKANG)
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

class PaymentTerm(TimestampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    days = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True, null=True)

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_terms"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UOM(TimestampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "uoms"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SalesNumberSequence(TimestampedModel):
    business_type = models.CharField(max_length=20, default="freight")
    period = models.CharField(max_length=6)  # YYYYMM
    prefix = models.CharField(max_length=30, default="FQ")
    padding = models.PositiveSmallIntegerField(default=5)
    last_no = models.PositiveIntegerField(default=0)

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_number_sequences"
        unique_together = (("business_type", "period"),)
        ordering = ["-period"]

    def __str__(self):
        return f"{self.business_type}-{self.period}: {self.prefix}/{str(self.last_no).zfill(self.padding)}"


class SalesQuotation(TimestampedModel):
    STATUS_DRAFT     = "DRAFT"
    STATUS_SENT      = "SENT"
    STATUS_ACCEPTED  = "ACCEPTED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_EXPIRED   = "EXPIRED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    ]

    # contoh field yang sudah ada:
    # number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    # valid_until = models.DateField(null=True, blank=True)  # pastikan ada field ini

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
        }.get(self.status, "bg-secondary")

    number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Partner, on_delete=PROTECT, related_name="quotations")
    date = models.DateField(null=True, blank=True)
    valid_until = models.DateField()
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))


    # relasi service by code (kolom DB varchar via db_column)
    sales_service = models.ForeignKey(
        SalesService,
        to_field="code",
        db_column="sales_service_id",
        on_delete=PROTECT,
        related_name="quotations",
    )

    # FK standar ke currencies.id (kolom DB = currency_id INTEGER)
    currency = models.ForeignKey(Currency, on_delete=PROTECT, related_name="quotations")

    payment_term = models.ForeignKey(
        PaymentTerm, on_delete=PROTECT, related_name="quotations", null=True, blank=True
    )

    # notes sesuai permintaan
    note_1 = models.TextField(blank=True, null=True)
    note_2 = models.TextField(blank=True, null=True)

    amount_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="DRAFT")
    business_type = models.CharField(max_length=20, default="freight")

    # info sales
    sales_user_id = models.IntegerField(null=True, blank=True)
    sales_agency = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name="agency_quotations"
    )
    # sales_reseller: DIHAPUS

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_quotations"


    def recalc_totals(self):
        """
        Hitung Σ(qty * price) dari semua line aktif dan simpan ke total_amount.
        """
        total = (
            self.lines.annotate(line_total=F("qty") * F("price"))
            .aggregate(s=Sum("line_total"))["s"]
            or Decimal("0.00")
        )
        self.total_amount = total
        self.save(update_fields=["total_amount"])
        return total

    def __str__(self):
        return self.number


class SalesQuotationLine(TimestampedModel):
    sales_quotation = models.ForeignKey(SalesQuotation, on_delete=CASCADE, related_name="lines")
    origin = models.ForeignKey(Location, on_delete=PROTECT, related_name="quotation_origin_lines")
    destination = models.ForeignKey(Location, on_delete=PROTECT, related_name="quotation_destination_lines")
    description = models.CharField(max_length=200, blank=True, null=True)
    uom = models.ForeignKey(UOM, on_delete=PROTECT)
    qty = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_quotation_lines"

    def __str__(self):
        return f"{self.description or ''} ({self.qty} {self.uom})"


class SalesOrder(TimestampedModel):
    number = models.CharField(max_length=50, unique=True)
    sales_quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        db_column="sales_quotation_id",
    )
    
    quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",              # <- hilangkan clashes "orders"
        db_column="quotation_id",      # <- kalau kolom lama ada
    )
    
    sales_service = models.ForeignKey(
        SalesService,
        to_field="code",
        db_column="sales_service_id",
        on_delete=PROTECT,
        related_name="services",
    )

    customer = models.ForeignKey(Partner, on_delete=PROTECT, related_name="orders")
    date = models.DateField(null=True, blank=True)

    currency = models.ForeignKey(Currency, on_delete=PROTECT, related_name="orders")
    payment_term = models.ForeignKey(
        PaymentTerm, on_delete=PROTECT, related_name="orders", null=True, blank=True
    )

    # order tidak pakai valid_until
    notes = models.TextField(blank=True, null=True)

    amount_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="DRAFT")
    business_type = models.CharField(max_length=20, default="freight")

    # info sales
    sales_user_id = models.IntegerField(null=True, blank=True)
    sales_agency = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name="agency_orders"
    )
    # sales_reseller: DIHAPUS

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_orders"

    def __str__(self):
        return self.number


class SalesOrderLine(TimestampedModel):
    sales_order = models.ForeignKey(SalesOrder, on_delete=CASCADE, related_name="lines")
    origin = models.ForeignKey(Location, on_delete=PROTECT, related_name="order_origin_lines")
    destination = models.ForeignKey(Location, on_delete=PROTECT, related_name="order_destination_lines")
    description = models.CharField(max_length=200, blank=True, null=True)
    uom = models.ForeignKey(UOM, on_delete=PROTECT)
    qty = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_order_lines"

    def __str__(self):
        return f"{self.description or ''} ({self.qty} {self.uom})"
