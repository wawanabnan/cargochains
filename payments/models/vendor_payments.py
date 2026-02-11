from django.db import models
from django.db.models import PROTECT
from django.utils import timezone

from partners.models import Vendor
from core.models.currencies import Currency
from accounting.models.chart import Account
from shipments.models.vendor_bills import VendorBill  # ganti kalau beda

class VendorPayment(models.Model):
    vb_number = models.CharField(max_length=30, unique=True, blank=True, default="")   # untuk finance
    letter_number = models.CharField(max_length=30, unique=True, blank=True, default="")  # untuk PO vendor (opsional)
    payment_date = models.DateField(default=timezone.localdate)

    vendor = models.ForeignKey(Vendor, on_delete=PROTECT, related_name="vendor_payments")
    currency = models.ForeignKey(Currency, on_delete=PROTECT, related_name="+")
    idr_rate = models.DecimalField(max_digits=18, decimal_places=6, default=1)

    cash_account = models.ForeignKey(
        Account, on_delete=PROTECT, related_name="+",
        help_text="Kas/Bank yang dipakai bayar"
    )
    reference = models.CharField(max_length=80, blank=True, default="")
    memo = models.TextField(blank=True, default="")

    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=10, default="DRAFT")  # DRAFT/POSTED/VOID

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
       
        db_table="vendor_payments"


    def recalc_total(self):
        self.total_amount = sum((x.amount for x in self.lines.all()), 0)
        return self.total_amount


class VendorPaymentLine(models.Model):
    payment = models.ForeignKey(VendorPayment, on_delete=models.CASCADE, related_name="lines")

    vendor_bill = models.ForeignKey(VendorBill, on_delete=PROTECT, null=True, blank=True, related_name="+")  # ✅ baru
    description = models.CharField(max_length=180, blank=True, default="")
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
       
        db_table="vendor_payment_lines"

