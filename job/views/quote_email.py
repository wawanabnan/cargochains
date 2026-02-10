import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from job.models.quotations import Quotation
from job.forms.quote_email import QuotationEmailForm

logger = logging.getLogger(__name__)

class QuotationSendEmailView(LoginRequiredMixin, View):
    def post(self, request, pk):
        q = get_object_or_404(Quotation, pk=pk)

        form = QuotationEmailForm(request.POST)
        if not form.is_valid():
            messages.error(
                request,
                "Form email tidak valid.",
                extra_tags="ui-modal",
            )
            return redirect("job:quotation_detail", pk=q.id)

        try:
            email = EmailMessage(
                subject=form.cleaned_data["subject"],
                body=form.cleaned_data["message"],
                to=form.cleaned_data["to"],
                cc=form.cleaned_data["cc"],
            )

            if form.cleaned_data.get("attach_pdf"):
                pdf_bytes, filename = self._render_quotation_pdf_bytes(request, q)
                email.attach(filename, pdf_bytes, "application/pdf")

            email.send()

            messages.success(
                request,
                "Email quotation berhasil dikirim.",
                extra_tags="ui-modal",
            )

        except Exception as e:
            messages.error(
                request,
                f"Gagal kirim email: {e}",
                extra_tags="ui-modal",
            )

        return redirect("job:quotation_detail", pk=q.id)
