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
            .select_related("job_order", "vendor", "payment_term", "approved_by")
            .prefetch_related("lines__taxes", "lines__uom", "lines__cost_type")
            .get(pk=pk)
        )

        lines = vb.lines.all().order_by("id")

        subtotal = sum((ln.amount or Decimal("0")) for ln in lines)
        tax_ppn = vb.ppn_amount
        tax_pph = vb.pph_amount

        total = subtotal + tax_ppn - tax_pph - (vb.discount_amount or Decimal("0"))

        # 🔥 Tambahkan ini
        signature_image = None
        signature_name = None
        signature_title = None

        if vb.approved_by:
            signature_name = vb.approved_by.get_full_name()
            signature_title = getattr(vb.approved_by, "title", "")
            signature_image = getattr(vb.approved_by, "signature", None)

        html = render_to_string(
            "service_orders/print/vb_pdf.html",
            {
                "vb": vb,
                "lines": lines,
                "subtotal": subtotal,
                "tax_ppn": tax_ppn,
                "tax_pph": tax_pph,
                "total": total,
                "signature_image": signature_image,
                "signature_name": signature_name,
                "signature_title": signature_title,
            },
            request=request,
        )

        base_url = request.build_absolute_uri("/")
        pdf_bytes = HTML(string=html, base_url=base_url).write_pdf()

        filename = f"VendorBooking-{vb.vb_number or vb.id}.pdf"
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        return resp