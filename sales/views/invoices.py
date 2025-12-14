# sales/views/invoices.py
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.views import View

from sales.invoice_model import Invoice
from sales.job_order_model import JobOrder
from sales.forms.invoices import InvoiceForm, InvoiceGenerateForm


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "invoices/list.html"
    context_object_name = "invoices"
    paginate_by = 20
    ordering = "-id"

    def get_queryset(self):
        qs = (
            Invoice.objects
            .select_related("job_order", "customer")
            .order_by("-id")
        )

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                number__icontains=q
            ) | qs.filter(
                customer__name__icontains=q
            ) | qs.filter(
                customer__company_name__icontains=q
            ) | qs.filter(
                job_order__number__icontains=q
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/form.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        obj: Invoice = form.save(commit=False)

        # autopopulate customer dari job_order (kalau field ada)
        jo = form.cleaned_data.get("job_order")
        if jo and hasattr(obj, "customer"):
            obj.customer = jo.customer

        obj.save()
        messages.success(self.request, "Invoice berhasil dibuat.")
        return redirect("sales:invoice_detail", pk=obj.pk)


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoices/invoice_form.html"
    context_object_name = "invoice"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        obj: Invoice = form.save(commit=False)

        jo = form.cleaned_data.get("job_order")
        if jo and hasattr(obj, "customer"):
            obj.customer = jo.customer

        obj.save()
        messages.success(self.request, "Invoice berhasil diupdate.")
        return redirect("sales:invoice_detail", pk=obj.pk)


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "sales/invoices/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        inv = self.object

        # modal generate (optional)
        ctx["generate_form"] = InvoiceGenerateForm()
        return ctx


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Invoice
    template_name = "sales/invoices/invoice_confirm_delete.html"
    context_object_name = "invoice"
    success_url = reverse_lazy("sales:invoice_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        num = getattr(obj, "number", obj.pk)
        messages.success(request, f"Invoice {num} berhasil dihapus.")
        return super().delete(request, *args, **kwargs)


class InvoiceGenerateFromJobOrderView(LoginRequiredMixin, View):
    """
    Buat invoice dari JobOrder (via modal di JobOrder detail atau Invoice detail).
    POST: job_order_id, mode, amount(optional), invoice_date, due_date, notes_*
    """
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        job_order_id = (request.POST.get("job_order_id") or "").strip()
        if not job_order_id.isdigit():
            messages.error(request, "Job Order tidak valid.")
            return redirect(request.META.get("HTTP_REFERER", reverse("sales:invoice_list")))

        jo = get_object_or_404(JobOrder, pk=int(job_order_id))

        form = InvoiceGenerateForm(request.POST)
        if not form.is_valid():
            messages.error(request, f"Gagal generate invoice: {form.errors.as_text()}")
            return redirect(request.META.get("HTTP_REFERER", reverse("sales:invoice_list")))

        cd = form.cleaned_data

        if cd["mode"] == InvoiceGenerateForm.MODE_FULL:
            amount = getattr(jo, "total_amount", None) or Decimal("0.00")
        else:
            amount = cd["amount"]

        inv = Invoice.objects.create(
            job_order=jo,
            customer=jo.customer if hasattr(Invoice, "customer") else None,
            invoice_date=cd["invoice_date"],
            due_date=cd["due_date"],
            subtotal_amount=amount,
            tax_amount=Decimal("0.00"),
            total_amount=amount,
            notes_customer=cd.get("notes_customer") or "",
            notes_internal=cd.get("notes_internal") or "",
        )

        messages.success(request, f"Invoice berhasil dibuat dari Job {jo.number}.")
        return redirect("sales:invoice_detail", pk=inv.pk)

from django.http import HttpResponse
from django.template.loader import render_to_string


class InvoicePrintView(LoginRequiredMixin, DetailView):
    model = Invoice
    context_object_name = "invoice"

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()

        # 1) Render HTML dari template
        html_string = render_to_string(
            "sales/invoices/print.html",
            {"invoice": invoice},
        )

        # 2) Siapkan command wkhtmltopdf
        wkhtmltopdf_cmd = getattr(settings, "WKHTMLTOPDF_CMD", "wkhtmltopdf")

        cmd = [
            wkhtmltopdf_cmd,
            "--encoding", "utf-8",
            "--enable-local-file-access",
            "-", "-"  # input dari stdin, output ke stdout
        ]

        try:
            proc = subprocess.run(
                cmd,
                input=html_string.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError:
            # fallback: tampilkan HTML kalau wkhtmltopdf tidak ketemu
            return HttpResponse(
                "wkhtmltopdf tidak ditemukan. cek settings.WKHTMLTOPDF_CMD.<br><br>"
                + html_string
            )

        if proc.returncode != 0:
            # kalau ada error dari wkhtmltopdf, kirim error & HTML untuk debug
            err = proc.stderr.decode("utf-8", errors="ignore")
            return HttpResponse(
                f"Error generate PDF (wkhtmltopdf exit {proc.returncode}):<br><pre>{err}</pre><hr>"
                + html_string
            )

        pdf_bytes = proc.stdout
        filename = f"Invoice-{invoice.number}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
