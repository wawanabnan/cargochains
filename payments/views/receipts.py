from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, DetailView

from payments.models.receipt import Receipt
from payments.forms.receipts import ReceiptForm
from payments.services.receipts import post_receipt


class ReceiptListView(LoginRequiredMixin, ListView):
    model = Receipt
    template_name = "receipts/list.html"
    context_object_name = "rows"
    paginate_by = 50


class ReceiptCreateView(LoginRequiredMixin, CreateView):
    model = Receipt
    form_class = ReceiptForm
    template_name = "receipts/form.html"

    def form_valid(self, form):
        rcpt = form.save(commit=False)

        # ✅ customer wajib mengikuti invoice
        rcpt.customer = rcpt.invoice.customer

        # ✅ default pph_withheld dari invoice kalau apply_pph
        if (rcpt.pph_withheld is None) or (rcpt.pph_withheld == Decimal("0.00")):
            if getattr(rcpt.invoice, "apply_pph", False):
                rcpt.pph_withheld = rcpt.invoice.pph_amount or Decimal("0.00")

        rcpt.save()
        messages.success(self.request, "Receipt created (Draft).")
        return redirect("payments:receipt_detail", pk=rcpt.pk)


class ReceiptDetailView(LoginRequiredMixin, DetailView):
    model = Receipt
    template_name = "payments/receipts/detail.html"
    context_object_name = "rcpt"


class ReceiptPostView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rcpt = get_object_or_404(Receipt, pk=pk)
        if not rcpt.can_post:
            messages.info(request, "Receipt already posted.")
            return redirect("payments:receipt_detail", pk=rcpt.pk)

        try:
            j = post_receipt(rcpt)
            messages.success(request, f"Receipt posted. Journal {j.number} created.")
        except ValidationError as e:
            messages.error(request, f"Gagal post receipt: {e}")

        return redirect("payments:receipt_detail", pk=rcpt.pk)
