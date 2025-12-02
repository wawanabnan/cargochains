# sales/invoice.py
from django.db import models
from django.db.models import PROTECT, CASCADE
from django.conf import settings
from django.utils import timezone

from core.models import TimeStampedModel, Currency, PaymentTerm, NumberSequence
from core.utils import get_next_number
from partners.models import Partner
from .freight import FreightOrder   # <-- INI YANG BENAR



# ============================
#   INVOICE STATUS
# ============================
class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent to customer"
    PARTIAL = "PARTIAL", "Partially Paid"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"



# ============================
#   INVOICE CATEGORY
# ============================

class InvoiceCategory(models.TextChoices):
    FREIGHT = "FREIGHT", "Freight"
    AGENCY = "AGENCY", "Agency"
    SHIP_CHARTER = "SHIP_CHARTER", "Ship Charter"


# ============================
#   INVOICE (HEADER)
# ============================
class Invoice(TimeStampedModel):
    """
    Invoice penagihan berdasarkan FreightOrder.
    Default desain: 1 FreightOrder -> 1 Invoice (OneToOneField).
    Kalau nanti perlu multi-invoice per order, ganti ke ForeignKey.
    """

    category = models.CharField(
        max_length=20,
        choices=InvoiceCategory.choices,
        default=InvoiceCategory.FREIGHT,
        help_text="Kategori bisnis invoice ini (Freight, Agency, Ship Charter, dll)."
    )

    number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Nomor invoice (auto generate dari NumberSequence)"
    )

    freight_order = models.ForeignKey(
        FreightOrder,
        on_delete=PROTECT,
        related_name="invoices",
    )

    # Snapshot informasi customer di saat invoice dibuat
    customer = models.ForeignKey(
        Partner,
        on_delete=PROTECT,
        related_name="customer_invoices",
    )

    # Informasi tanggal & pembayaran
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()

    currency = models.ForeignKey(
        Currency,
        on_delete=PROTECT,
        related_name="currency_invoices",
    )

    payment_term = models.ForeignKey(
        PaymentTerm,
        on_delete=PROTECT,
        related_name="payment_invoices",
    )

    # Ringkasan nilai
    subtotal_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )
    tax_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )
    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Total yang ditagihkan ke customer."
    )
    amount_paid = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Total pembayaran yang sudah diterima."
    )

    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )

    # Catatan
    notes_internal = models.TextField(
        blank=True,
        help_text="Catatan internal, tidak tampil di invoice customer."
    )
    notes_customer = models.TextField(
        blank=True,
        help_text="Catatan yang akan tampil di invoice (footer / remarks)."
    )

    # Audit user
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        related_name="invoices_created",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        related_name="invoices_updated",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-invoice_date", "-id"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return self.number or f"Invoice for {self.freight_order}"

    # -----------------------------
    #   HELPER & BUSINESS LOGIC
    # -----------------------------
    @property
    def amount_outstanding(self):
        """Sisa tagihan."""
        return (self.total_amount or 0) - (self.amount_paid or 0)

    @property
    def is_paid(self):
        return self.status == InvoiceStatus.PAID

    def save(self, *args, **kwargs):
        # Auto-generate number jika belum ada
        if not self.number:
            # Pastikan sudah ada NumberSequence: (app_label='sales', key='FREIGHT_INVOICE')
            self.number = get_next_number("sales", "INVOICE")

        # Kalau due_date belum diisi, set default = invoice_date
        if not self.due_date:
            self.due_date = self.invoice_date

        super().save(*args, **kwargs)


    @property
    def description(self):
        """
        Deskripsi invoice yang diambil dari FreightOrder:
        'Freight Order No XXX - SalesService Origin - Destination CargoName'
        """
        fo = self.freight_order
        if not fo:
            return ""

        parts = []

        # No Freight Order
        if getattr(fo, "number", None):
            parts.append(f"Freight Order No {fo.number}")

        # Sales Service (misal: Sea - Door to Door)
        sales_service = getattr(fo, "sales_service", None)
        if sales_service and getattr(sales_service, "name", None):
            parts.append(sales_service.name)

        # Origin - Destination
        origin = getattr(fo, "origin", None)
        destination = getattr(fo, "destination", None)

        if origin and getattr(origin, "name", None) and destination and getattr(destination, "name", None):
            parts.append(f"{origin.name} - {destination.name}")
        elif origin and getattr(origin, "name", None):
            parts.append(origin.name)
        elif destination and getattr(destination, "name", None):
            parts.append(destination.name)

        # Cargo name
        cargo_name = getattr(fo, "cargo_name", None)
        if cargo_name:
            parts.append(cargo_name)

        return " - ".join(parts)


    # -----------------------------
    #   FACTORY: BUAT DARI ORDER
    # -----------------------------
    @classmethod
    def create_from_freight_order(cls, freight_order, user=None, invoice_date=None):
        """
        Buat invoice dari FreightOrder:
        - category otomatis FREIGHT
        - salin customer, currency, payment_term
        - salin nilai subtotal, tax, total dari FreightOrder
        """
        if invoice_date is None:
            invoice_date = timezone.now().date()

        obj = cls(
            category=InvoiceCategory.FREIGHT,
            freight_order=freight_order,
            customer=freight_order.customer,
            currency=getattr(freight_order, "currency", None),
            payment_term=getattr(freight_order, "payment_term", None),
            invoice_date=invoice_date,
            due_date=invoice_date,
            created_by=user,
            updated_by=user,
        )

        # SESUAIKAN NAMA FIELD FO DI SINI
        obj.subtotal_amount = getattr(freight_order, "subtotal_amount", 0) or 0
        obj.tax_amount = getattr(freight_order, "tax_amount", 0) or 0
        obj.total_amount = getattr(freight_order, "total_amount", 0) or 0

        obj.save()
        return obj


# ============================
#   FREIGHT INVOICE LINE
# ============================
class InvoiceLine(TimeStampedModel):
    """
    Detail invoice (baris-baris biaya).
    Untuk simple case: 1 invoice bisa terdiri dari beberapa charge.
    Belum di-link langsung ke FreightOrderLine supaya aman.
    Nanti kalau FO sudah pakai line, bisa ditambahkan FK opsional.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=CASCADE,
        related_name="lines",
    )

    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=18, decimal_places=3, default=1)
    uom = models.CharField(max_length=20, blank=True)  # kalau mau, nanti bisa FK ke UOM model
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["invoice", "sort_order", "id"]

    def __str__(self):
        return self.description or f"Line {self.pk}"

    def save(self, *args, **kwargs):
        # Hitung amount jika belum diisi
        if not self.amount:
            self.amount = (self.quantity or 0) * (self.unit_price or 0)
        super().save(*args, **kwargs)



