from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from billing.models.customer_invoice import Invoice


class InvoicePreviewView(LoginRequiredMixin, View):
    """
    HTML Preview Invoice (A4 simulation).
    Tidak generate PDF.
    """

    def get(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=pk)

        return render(
            request,
            "customer_invoices/invoice_preview.html",  # extend base_preview_letterhead
            {
                "invoice": invoice,
            },
        )