# sales/invoice.py
from django.db import models
from django.db.models import PROTECT, CASCADE
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

from core.models import TimeStampedModel, Currency, PaymentTerm,Tax
from core.utils import get_next_number
from partners.models import Partner,Customer
from .job_order_model import JobOrder


class Invoice(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_UNPAID = "UNPAID"
    STATUS_PAID = "PAID"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PAID, "Paid"),
    ]

    number = models.CharField(max_length=30, unique=True, editable=False)

    # optional (jika invoice dari JobOrder)
    job_order = models.ForeignKey(
        JobOrder, on_delete=PROTECT, null=True, blank=True, related_name="invoices"
    )

    
    customer = models.ForeignKey(
        Customer,
        on_delete=PROTECT,
        related_name="customer_invoices",
        verbose_name="Customer",
        
    )

    tax = models.ForeignKey(Tax, on_delete=models.PROTECT, null=True, blank=True)

    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)

    currency = models.ForeignKey(Currency, on_delete=PROTECT, null=True, blank=True)
    payment_term = models.ForeignKey(PaymentTerm, on_delete=PROTECT, null=True, blank=True)

    subtotal_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    apply_pph = models.BooleanField(default=False)
    pph_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    pph_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))


    amount_paid = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    notes_internal = models.TextField(blank=True, default="")
    notes_customer = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=PROTECT,
        related_name="invoices_created", null=True, blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=PROTECT,
        related_name="invoices_updated", null=True, blank=True
    )

    class Meta:
        ordering = ["-invoice_date", "-id"]

    def __str__(self):
        return self.number

    def clean(self):
        # kalau manual (tanpa job) -> customer wajib
        if not self.job_order and not self.customer:
            raise ValidationError({"customer": "Customer wajib diisi untuk invoice manual."})

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = get_next_number("sales", "INVOICE")

        # auto set dari JobOrder
        if self.job_order:
            if not self.customer:
                self.customer = getattr(self.job_order, "customer", None)
            if not self.currency:
                self.currency = getattr(self.job_order, "currency", None)
            if not self.payment_term:
                self.payment_term = getattr(self.job_order, "payment_term", None)

        if not self.due_date:
            self.due_date = self.invoice_date

        super().save(*args, **kwargs)


class InvoiceLine(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("1.00"))
    price = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    taxes = models.ManyToManyField(Tax, blank=True, related_name="invoice_lines")

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        db_table = "sales_invoice_lines"

    def save(self, *args, **kwargs):
        self.amount = (self.quantity or 0) * (self.price or 0)
        super().save(*args, **kwargs)
