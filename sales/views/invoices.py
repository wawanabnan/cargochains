# sales/views/invoices.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView

from sales.invoice import Invoice, InvoiceCategory


from .freight import FreightOrder
from ..forms import InvoiceForm, InvoiceGenerateForm
from django.views.generic import ListView, CreateView

# sales/views/invoices.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, FormView
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404


from django.shortcuts import redirect, get_object_or_404
from django.views.generic import DetailView, UpdateView, ListView, CreateView
from django.contrib import messages
from sales.invoice import Invoice, InvoiceCategory, InvoiceStatus
from sales.freight import FreightOrder
from sales.forms import InvoiceForm

import subprocess
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoices/form.html"

    def get_initial(self):
        """
        Kalau ada ?fo=ID di URL, prefill freight_order + tanggal + amount dari FreightOrder.
        """
        initial = super().get_initial()
        fo_id = self.request.GET.get("fo")
        if fo_id:
            try:
                fo = FreightOrder.objects.get(pk=fo_id)
                initial["freight_order"] = fo
                today = timezone.now().date()
                initial["invoice_date"] = today
                initial["due_date"] = today
                initial["subtotal_amount"] = getattr(fo, "subtotal_amount", 0) or 0
                initial["tax_amount"] = getattr(fo, "tax_amount", 0) or 0
                initial["total_amount"] = getattr(fo, "total_amount", 0) or 0
            except FreightOrder.DoesNotExist:
                pass
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """
        Saat form valid:
        - set category = FREIGHT
        - copy customer, currency, payment_term dari FreightOrder
        - kalau amount masih 0, copy dari FreightOrder juga
        """
        obj = form.save(commit=False)
        fo: FreightOrder = obj.freight_order

        # kategori bisnis
        obj.category = InvoiceCategory.FREIGHT

        # informasi dari FreightOrder
        obj.customer = fo.customer

        if hasattr(fo, "currency") and fo.currency_id:
            obj.currency = fo.currency
        if hasattr(fo, "payment_term") and fo.payment_term_id:
            obj.payment_term = fo.payment_term

        # kalau user tidak isi angka, pakai angka dari FreightOrder
        if not obj.subtotal_amount:
            obj.subtotal_amount = getattr(fo, "subtotal_amount", 0) or 0
        if not obj.tax_amount:
            obj.tax_amount = getattr(fo, "tax_amount", 0) or 0
        if not obj.total_amount:
            obj.total_amount = getattr(fo, "total_amount", 0) or 0

        obj.created_by = self.request.user
        obj.updated_by = self.request.user
        obj.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("sales:invoice_list")




# sales/views/invoices.py


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "sales/invoices/list.html"
    context_object_name = "invoices"
    paginate_by = 20  # bisa diubah

    def get_queryset(self):
        qs = (
            Invoice.objects
            .select_related("freight_order", "customer", "currency")
            .order_by("-invoice_date", "-id")
        )

        q = self.request.GET.get("q")
        status = self.request.GET.get("status")

        if q:
            qs = qs.filter(number__icontains=q)

        if status:
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_filter"] = self.request.GET.get("status", "")
        # opsi status untuk filter dropdown
        ctx["status_choices"] = self.model._meta.get_field("status").choices
        return ctx


class InvoiceGenerateView(LoginRequiredMixin, FormView):
    template_name = "sales/invoices/generate.html"
    form_class = InvoiceGenerateForm

    def dispatch(self, request, *args, **kwargs):
        # Ambil FreightOrder dari URL
        self.freight_order = get_object_or_404(FreightOrder, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        fo = self.freight_order
        today = timezone.now().date()
        initial["invoice_date"] = today
        initial["due_date"] = today

        # Mode default: FULL → amount awal = total FO
        total_fo = getattr(fo, "total_amount", 0) or 0
        initial["amount"] = total_fo
        initial["mode"] = InvoiceGenerateForm.MODE_FULL

        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["freight_order"] = self.freight_order
        ctx["total_fo"] = getattr(self.freight_order, "total_amount", 0) or 0
        return ctx

    def form_valid(self, form):
        fo = self.freight_order
        mode = form.cleaned_data["mode"]
        invoice_date = form.cleaned_data["invoice_date"]
        due_date = form.cleaned_data["due_date"]
        notes_customer = form.cleaned_data["notes_customer"]
        notes_internal = form.cleaned_data["notes_internal"]

        # Tentukan nilai amount
        total_fo = getattr(fo, "total_amount", 0) or 0
        if mode == InvoiceGenerateForm.MODE_FULL:
            amount = total_fo
        else:
            amount = form.cleaned_data["amount"]

        # Buat Invoice otomatis (ini inti "generate")
        inv = Invoice.objects.create(
            category=InvoiceCategory.FREIGHT,
            freight_order=fo,
            customer=fo.customer,
            currency=getattr(fo, "currency", None),
            payment_term=getattr(fo, "payment_term", None),
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal_amount=amount,  # sementara treat semua sebagai subtotal
            tax_amount=0,            # nanti bisa dipecah kalau om mau
            total_amount=amount,
            amount_paid=0,
            notes_customer=notes_customer,
            notes_internal=notes_internal,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

        messages.success(self.request, f"Invoice {inv.number} berhasil dibuat dari Freight Order {fo}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("sales:invoice_list")


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "sales/invoices/detail.html"
    context_object_name = "invoice"


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoices/detail.html"  # pakai template yang sama
    context_object_name = "invoice"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.status != InvoiceStatus.DRAFT:
            messages.error(request, "Invoice hanya bisa diedit saat status DRAFT.")
            return redirect("sales:invoice_detail", pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.updated_by = self.request.user
        obj.save()
        messages.success(self.request, "Invoice berhasil diupdate.")
        return redirect("sales:invoice_detail", pk=obj.pk)


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
