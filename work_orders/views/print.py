from decimal import Decimal
from django.views.generic import DetailView
from work_orders.models.vendor_bookings         import VendorBooking, VendorBookingLine

class VendorBookingPrintView(DetailView):
    model = VendorBooking
    template_name = "service_orders/print/vb_preview.html"
    context_object_name = "vb"

    from decimal import Decimal
from django.views.generic import DetailView
from work_orders.models.vendor_bookings import VendorBooking

class VendorBookingPrintView(DetailView):
    model = VendorBooking
    template_name = "service_orders/print/vb_preview.html"
    context_object_name = "vb"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        vb = (
            VendorBooking.objects
            .select_related("job_order", "vendor", "payment_term")
            .prefetch_related("lines__taxes", "lines__uom", "lines__cost_type")
            .get(pk=ctx["vb"].pk)
        )

        lines = vb.lines.all().order_by("id")

        subtotal = sum((ln.amount or Decimal("0")) for ln in lines)
        tax_ppn = vb.ppn_amount
        tax_pph = vb.pph_amount

        total = subtotal + tax_ppn - tax_pph - (vb.discount_amount or Decimal("0"))

        ctx.update({
            "vb": vb,
            "lines": lines,
            "subtotal": subtotal,
            "tax_ppn": tax_ppn,
            "tax_pph": tax_pph,
            "total": total,
        })
        return ctx
