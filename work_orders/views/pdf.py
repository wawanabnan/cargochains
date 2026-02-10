from decimal import Decimal
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
from weasyprint import HTML
from work_orders.models.vendor_bookings import VendorBooking

class VendorBookingPdfView(View):
    def get(self, request, pk: int):
        vb = (
            VendorBooking.objects
            .select_related("job_order", "vendor", "payment_term")
            .prefetch_related("lines__taxes", "lines__uom", "lines__cost_type")
            .get(pk=pk)
        )

        lines = vb.lines.all().order_by("id")

        subtotal = sum((ln.amount or Decimal("0")) for ln in lines)
        tax_ppn = vb.ppn_amount
        tax_pph = vb.pph_amount

        total = subtotal + tax_ppn - tax_pph - (vb.discount_amount or Decimal("0"))

        html = render_to_string(
            "vendor_bookings/print/vb_pdf.html",
            {
                "vb": vb,
                "lines": lines,
                "subtotal": subtotal,
                "tax_ppn": tax_ppn,
                "tax_pph": tax_pph,
                "total": total,
            },
            request=request,
        )

        base_url = request.build_absolute_uri("/")
        pdf_bytes = HTML(string=html, base_url=base_url).write_pdf()

        filename = f"VendorBooking-{vb.vb_number or vb.id}.pdf"
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        return resp
