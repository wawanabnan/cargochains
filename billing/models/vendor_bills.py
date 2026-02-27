from django.db import models
from django.db.models import PROTECT, Sum
from django.utils import timezone

from partners.models import Partner
from core.models.currencies import Currency
from work_orders.models.vendor_bookings import VendorBooking  # kalau memang ada
from core.models.taxes import Tax

class VendorBill(models.Model):
    bill_number = models.CharField(max_length=40, unique=True)  # nomor invoice dari vendor
    bill_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)

    vendor = models.ForeignKey(Partner, on_delete=PROTECT, related_name="vendor_bills")
    currency = models.ForeignKey(Currency, on_delete=PROTECT, related_name="+")
    idr_rate = models.DecimalField(max_digits=18, decimal_places=6, default=1)

    reference = models.CharField(max_length=80, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=10, default="DRAFT")  # DRAFT/POSTED/VOID
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_bills"

    def recalc_total(self):
        self.total_amount = sum((x.amount for x in self.lines.all()), 0)
        return self.total_amount

    def paid_amount(self):
        # dihitung dari VendorPaymentLine yang POSTED dan refer ke bill ini
        from billing.models.vendor_payment import VendorPaymentLine  # import local biar gak circular
        agg = VendorPaymentLine.objects.filter(
            vendor_bill=self,
            payment__status="POSTED",
        ).aggregate(s=Sum("amount"))
        return agg["s"] or 0

    def balance_amount(self):
        return (self.total_amount or 0) - (self.paid_amount() or 0)


class VendorBillLine(models.Model):
    bill = models.ForeignKey(VendorBill, on_delete=models.CASCADE, related_name="lines")
    vendor_booking = models.ForeignKey(VendorBooking, on_delete=PROTECT, null=True, blank=True, related_name="+")
    description = models.CharField(max_length=180, blank=True, default="")
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    taxes= taxes = models.ManyToManyField(
        Tax,
        blank=True,
        related_name="vendor_bill_lines",
    )
  
    class Meta:
        db_table = "vendor_bill_lines"
