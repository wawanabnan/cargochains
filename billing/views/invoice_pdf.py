# sales/views/invoice_pdf_html.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View

from weasyprint import HTML
from billing.models.customer_invoice import Invoice


class InvoicePdfHtmlView(LoginRequiredMixin, View):
    """
    Generate PDF Invoice menggunakan WeasyPrint
    Layout dan header/footer dikontrol via CSS @page.
    """

    def get(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=pk)

        html_string = render_to_string(
            "invoice/invoice_pdf.html",  # <-- extend base_pdf_letterhead
            {
                "invoice": invoice,
            },
            request=request,
        )

        # penting agar static() dan image kebaca
        base_url = request.build_absolute_uri("/")

        pdf_file = HTML(
            string=html_string,
            base_url=base_url
        ).write_pdf()

        filename = (
            f"INV-{invoice.number}.pdf"
            if getattr(invoice, "number", None)
            else "Invoice.pdf"
        )

        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response