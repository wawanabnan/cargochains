from decimal import Decimal
from django.db.models import Sum
from sales.models import Invoice

D0 = Decimal("0.00")


class SalesRevenueReportService:
    VALID_STATUSES = [Invoice.ST_SENT, Invoice.ST_PAID]

    def get_queryset(self, *, date_from=None, date_to=None, customer_id=None, currency=None):
        qs = Invoice.objects.filter(
            status__in=self.VALID_STATUSES
        ).select_related("customer", "currency")

        if date_from:
            qs = qs.filter(invoice_date__gte=date_from)
        if date_to:
            qs = qs.filter(invoice_date__lte=date_to)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if currency:
            qs = qs.filter(currency__code__iexact=currency)

        # 🔥 DESC biar terbaru di atas
        return qs.order_by("-invoice_date", "-number", "-id")

    def build(self, **filters):
        qs = self.get_queryset(**filters)
        totals = qs.aggregate(
            subtotal=Sum("subtotal_amount"),
            tax=Sum("tax_amount"),
            total=Sum("total_amount"),
            total_idr=Sum("total_idr"),         # ✅ NEW
        )
        return qs, {
            "subtotal": totals["subtotal"] or D0,
            "tax": totals["tax"] or D0,
            "total": totals["total"] or D0,
            "total_idr": totals["total_idr"] or D0,   # ✅ NEW
        }
