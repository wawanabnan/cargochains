from django.db import models
from django.db.models import PROTECT
from django.utils import timezone

from accounting.models.chart import Account
from accounting.models.journal import Journal
from billing.models.customer_invoice import Invoice,InvoiceLine
from partners.models import Customer

class CustomerReceipt(models.Model):
    ST_DRAFT = "draft"
    ST_POSTED = "posted"
    STATUS_CHOICES = [
        (ST_DRAFT, "Draft"),
        (ST_POSTED, "Posted"),
    ]

    receipt_no = models.CharField(max_length=30, unique=True, blank=True)
    receipt_date = models.DateField(default=timezone.now)

    invoice = models.ForeignKey(Invoice, on_delete=PROTECT, related_name="receipts")
    
    customer = models.ForeignKey(
        Customer,
        on_delete=PROTECT,
        related_name="receipts",
    )


    amount = models.DecimalField(max_digits=18, decimal_places=2)
    cash_account = models.ForeignKey(
        Account, on_delete=PROTECT, related_name="+", null=True, blank=True
    )
    pph_withheld = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ST_DRAFT)
    journal = models.OneToOneField(
        Journal, on_delete=PROTECT, null=True, blank=True, related_name="receipt"
    )

    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-receipt_date", "-id"]
        db_table="customer_receipts"

    def __str__(self):
        return self.receipt_no or f"RCPT-{self.id}"

    @property
    def can_post(self):
        return self.status == self.ST_DRAFT and self.journal_id is None
