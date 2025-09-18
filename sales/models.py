# sales/models.py
from django.db import models
from django.db.models import PROTECT, CASCADE
from partners.models import Partner
from geo.models import Location


class Currency(models.Model):
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


class SalesService(models.Model):
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


class PaymentTerm(models.Model):
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


class UOM(models.Model):
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


class SalesNumberSequence(models.Model):
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


class SalesQuotation(models.Model):
    number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Partner, on_delete=PROTECT, related_name="quotations")
    date = models.DateField(null=True, blank=True)
    valid_until = models.DateField()

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

    # timestamps (PALING BELAKANG)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_quotation_lines"

    def __str__(self):
        return f"{self.description or ''} ({self.qty} {self.uom})"


class SalesOrder(models.Model):
    number = models.CharField(max_length=50, unique=True)
    quotation = models.ForeignKey(
        SalesQuotation, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
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


class SalesOrderLine(models.Model):
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
