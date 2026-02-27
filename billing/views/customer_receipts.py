from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, DetailView

from billing.models.customer_receipt import  CustomerReceipt
from billing.forms.customer_receipts  import CustomerReceiptForm
from billing.services.customer_receipts import CustomerReceipt


class CustomerReceiptListView(LoginRequiredMixin, ListView):
    model = CustomerReceipt
    template_name = "customer_receipts/list.html"
    context_object_name = "rows"
    paginate_by = 50


class CustomerReceiptCreateView(LoginRequiredMixin, CreateView):
    model = CustomerReceipt
    form_class = CustomerReceiptForm
    template_name = "customer_receipts/form.html"

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
        return redirect("billing:receipt_detail", pk=rcpt.pk)


class CustomerReceiptDetailView(LoginRequiredMixin, DetailView):
    model = CustomerReceipt
    template_name = "billing/receipts/detail.html"
    context_object_name = "rcpt"


class CustomerReceiptPostView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rcpt = get_object_or_404(CustomerReceipt, pk=pk)
        if not rcpt.can_post:
            messages.info(request, "Receipt already posted.")
            return redirect("billing:receipt_detail", pk=rcpt.pk)

        try:
            j = post_receipt(rcpt)
            messages.success(request, f"Receipt posted. Journal {j.number} created.")
        except ValidationError as e:
            messages.error(request, f"Gagal post receipt: {e}")

        return redirect("billing:customer_receipts_detail", pk=rcpt.pk)
