# billing/views/invoices.py
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, CreateView

#from sales.job_order_model import JobOrder
from job.models.job_orders import JobOrder

from billing.models.customer_invoice import Invoice,InvoiceLine

from billing.forms.invoices import InvoiceForm, InvoiceLineFormSet

from billing.utils.invoices import build_invoice_description
from decimal import Decimal, ROUND_HALF_UP
from core.models.taxes import Tax
from billing.utils.permissions import is_finance
from django.core.exceptions import PermissionDenied
from accounting.services.invoice_posting import create_journal_from_invoice
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from django.core.exceptions import PermissionDenied
from decimal import Decimal, InvalidOperation

from core.models.settings import CoreSetting  # sesuaikan nama model core settings om
from core.services.exchange_rates import get_rate_to_idr  # ✅ new
from billing.utils.template_renderer import render_billing_text
from billing.models.config import BillingConfig




# =========================================================
# Helpers
# =========================================================
def _build_tax_map():
    qs = Tax.objects.filter(is_active=True).only("id", "rate", "is_withholding")
    return {
        str(t.id): {
            "rate": float(t.rate or Decimal("0")),          # percent
            "is_withholding": bool(t.is_withholding),
        }
        for t in qs
    }


def invoice_refresh_payment_status(inv: Invoice, save=True):
    """
    Status:
      - Draft tetap draft sampai user ubah (opsional)
      - Jika amount_paid >= total_amount => PAID
      - Selain itu => UNPAID
    """
    total = inv.total_amount or Decimal("0")
    paid = inv.amount_paid or Decimal("0")

    if getattr(inv, "status", None) == "DRAFT":
        if save:
            inv.save(update_fields=["status"])
        return

    if total > 0 and paid >= total:
        inv.status = "PAID"
    else:
         inv.status = Invoice.ST_SENT

    if save:
        inv.save(update_fields=["status"])


def _line_price_field_name():
    """
    InvoiceLine di project om kadang pakai 'price', kadang 'unit_price'.
    Kita deteksi supaya recalc aman.
    """
    names = {f.name for f in InvoiceLine._meta.fields}
    return "unit_price" if "unit_price" in names else "price"

def _q2(x):
    return (x or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def recalc_invoice_totals(invoice: Invoice):
    lines = invoice.lines.all().prefetch_related("taxes")

    subtotal = Decimal("0")
    base_by_tax = {}  # tax_id -> base amount

    for ln in lines:
        amt = _q2((ln.quantity or 0) * (ln.price or 0))
        subtotal += amt
        for tx in ln.taxes.all():
            base_by_tax[tx.id] = base_by_tax.get(tx.id, Decimal("0")) + amt

    tax_total = Decimal("0")
    if base_by_tax:
        taxes = Tax.objects.in_bulk(base_by_tax.keys())
        for tax_id, base in base_by_tax.items():
            tx = taxes.get(tax_id)
            if not tx:
                continue
            rate = Decimal(str(tx.rate or 0))
            tax_total += _q2(base * rate / Decimal("100"))

    subtotal = _q2(subtotal)
    tax_total = _q2(tax_total)
    total = _q2(subtotal + tax_total)

    invoice.subtotal_amount = subtotal
    invoice.tax_amount = tax_total
    invoice.total_amount = total
    invoice.recalc_total_idr()
    invoice.save(update_fields=["subtotal_amount", "tax_amount", "total_amount", "exchange_rate", "total_idr"])

from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

def get_ppn_11_tax():
    # prioritas: rate 1.10 / 1.1
    for r in (Decimal("1.10"), Decimal("1.1")):
        try:
            return Tax.objects.get(rate=r)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            pass

    # fallback: cari nama mengandung "PPN" dan "1.1"
    q = Tax.objects.filter(name__icontains="ppn").filter(name__icontains="1.1")
    if q.exists():
        return q.first()

    raise ValueError("Master Tax PPN 1.1% tidak ditemukan. Buat dulu di tabel Tax.")

# =========================================================
# Views
# =========================================================
class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "customer_invoices/list.html"
    context_object_name = "invoices"
    paginate_by = 12
    ordering = ["-number"]

    def get_queryset(self):
        
        qs = (
            Invoice.objects
            .all()
            .select_related("customer")   # kalau field customer ada
            .order_by("-number")
        )
        return qs

    
class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "customer_invoices/detail.html"
    context_object_name = "invoice"
    job = None 

    def calc_invoice_totals(invoice):
        sub = Decimal("0.00")
        tax = Decimal("0.00")

        for ln in invoice.lines.all():  # related_name="lines" :contentReference[oaicite:1]{index=1}
            line_amount = ln.amount or Decimal("0.00")  # amount sudah ada :contentReference[oaicite:2]{index=2}
            sub += line_amount

            # taxes = M2M :contentReference[oaicite:3]{index=3}
            for tx in ln.taxes.all():
                # asumsi tx.rate adalah persen (mis. 11 untuk 11%)
                rate = getattr(tx, "rate", None)
                if rate:
                    tax += (line_amount * Decimal(str(rate)) / Decimal("100"))

        total = sub + tax
        return sub, tax, total

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        inv = ctx["invoice"]

        # ==========================
        # FORMSET (existing code)
        # ==========================
        if self.request.method == "POST":
            ctx["formset"] = InvoiceLineFormSet(self.request.POST)
        else:
            fs = InvoiceLineFormSet()

            if fs.forms and self.job:
                price_key = "price"

                base_amount = getattr(self.job, "subtotal_amount", None)
                if base_amount is None:
                    base_amount = getattr(self.job, "total_amount", 0) or 0

                fs.forms[0].initial = {
                    "description": build_invoice_description(self.job),
                    "quantity": 1,
                    price_key: base_amount,
                }

                ppn11 = get_ppn_11_tax()
                if ppn11 and "taxes" in fs.forms[0].fields:
                    fs.forms[0].initial["taxes"] = [ppn11.pk]

            ctx["formset"] = fs

        # ==========================
        # EXISTING CONTEXT
        # ==========================
        ctx["mode"] = "from_job" if inv.job_order_id else "manual"
        ctx["job_order"] = self.job
        ctx["can_confirm"] = inv.can_confirm(self.request.user)

        # ==========================
        # FX RATE
        # ==========================
        code = (getattr(inv.currency, "code", "") or "").upper()
        if code == "IDR" or not code:
            ctx["suggested_rate"] = Decimal("1.0")
        else:
            rate = get_rate_to_idr(inv.currency, inv.invoice_date)
            ctx["suggested_rate"] = rate or inv.exchange_rate or Decimal("1.0")

        # ==========================
        # BILLING CONFIG (NEW)
        # ==========================
        config = BillingConfig.get_solo()
        ctx["billing_config"] = config

        ctx["rendered_terms"] = render_billing_text(
            config.default_terms_conditions,
            inv
        )

        ctx["rendered_customer_note"] = render_billing_text(
            config.default_customer_note,
            inv
        )

        return ctx
    
class InvoiceCreateManualView(LoginRequiredMixin, View):
    template_name = "customer_invoices/form.html"

    def get(self, request):
        form = InvoiceForm()
        formset = InvoiceLineFormSet()

        context = {
            "form": form,
            "formset": formset,
            "mode": "manual",
            "tax_map": _build_tax_map(),  # 👈 penting untuk select2 + js tax
        }

        return render(request, self.template_name, context)


    @transaction.atomic
    def post(self, request):
        form = InvoiceForm(request.POST)
        formset = InvoiceLineFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            inv = form.save(commit=False)

            # safety anti-null
            inv.subtotal_amount = inv.subtotal_amount or Decimal("0.00")
            inv.tax_amount = inv.tax_amount or Decimal("0.00")
            inv.total_amount = inv.total_amount or Decimal("0.00")

            inv.save()  # ✅ WAJIB sebelum formset.save()

            formset.instance = inv
            formset.save()

            recalc_invoice_totals(inv)  # ✅ source of truth
            messages.success(request, "Invoice berhasil dibuat.")
            return redirect("billing:invoice_detail", pk=inv.pk)


        if not (form.is_valid() and formset.is_valid()):
            messages.error(request, "VALIDATION ERROR — periksa data berikut:")

            if form.errors:
                messages.error(request, f"Header: {form.errors.as_text()}")

            if formset.non_form_errors():
                messages.error(request, f"Lines: {formset.non_form_errors()}")

            for i, errs in enumerate(formset.errors, start=1):
                if errs:
                    messages.error(request, f"Line #{i}: {errs}")

            return render(
                request,
                self.template_name,
                {   
                    "form": form, 
                    "formset": formset, 
                    "mode": "manual",
                    "tax_map": _build_tax_map(),
                }
            )


        return render(request, self.template_name, {"form": form, "formset": formset, "mode": "manual"})



class InvoiceDeleteView(LoginRequiredMixin, View):
    template_name = "customer_invoices/invoice_confirm_delete.html"

    def get(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)
        return render(request, self.template_name, {"invoice": inv})

    @transaction.atomic
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)
        inv.delete()
        messages.success(request, "Invoice berhasil dihapus.")
        return redirect("billing:invoice_list")



class InvoiceMarkPaidView(LoginRequiredMixin, View):
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)
        inv.amount_paid = inv.total_amount
        invoice_refresh_payment_status(inv, save=False)
        inv.save(update_fields=["amount_paid", "status"])

        messages.success(request, "Invoice ditandai PAID.")
        return redirect("billing:invoice_detail", pk=inv.pk)


class InvoiceChangeStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)

        from billing.utils.permissions import is_finance
        if not is_finance(request.user):
            raise PermissionDenied("Hanya Finance yang boleh ubah status invoice.")

        inv.status = request.POST.get("status", inv.status)
        if hasattr(inv, "updated_by_id"):
            inv.updated_by = request.user
        inv.save(update_fields=["status", "updated_by"] if hasattr(inv, "updated_by_id") else ["status"])

        return redirect("billing:invoice_detail", pk=inv.pk)


class InvoiceUpdateView(LoginRequiredMixin, View):
    template_name = "customer_invoices/form.html"

    def get(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)

        form = InvoiceForm(instance=inv)
        formset = InvoiceLineFormSet(instance=inv)
        return render(
            request,
            self.template_name,
            {
                "form": form, 
                "formset": formset, 
                "mode": "edit", 
                "invoice": inv,
                "tax_map": _build_tax_map(),
            },
        )

    @transaction.atomic
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)

      
        form = InvoiceForm(request.POST, instance=inv)
        formset = InvoiceLineFormSet(request.POST, instance=inv)

        if form.is_valid() and formset.is_valid():
            inv = form.save()
            formset.save()  # ✅ include M2M taxes
            recalc_invoice_totals(inv)

            messages.success(request, "Invoice berhasil diupdate.")
            return redirect("billing:invoice_detail", pk=inv.pk)

        messages.error(request, "VALIDATION ERROR — cek detail di bawah.")
        messages.error(request, f"HEADER(form) errors:\n{form.errors.as_text()}")
        messages.error(request, f"LINE(formset) non_form_errors:\n{formset.non_form_errors()}")
        messages.error(request, f"LINE(formset) errors:\n{formset.errors}")

        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "mode": "edit", "invoice": inv, "tax_map": _build_tax_map()},
        )



def get_int_setting(code: str, default: int = 0) -> int:
    row = CoreSetting.objects.filter(code=code).first()
    if not row:
        return default
    return int(row.int_value or 0)


class InvoiceConfirmView(View):
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)

        if not inv.can_confirm(request.user):
            raise PermissionDenied

        if inv.journal_id:
            messages.info(request, f"Invoice {inv.number} sudah memiliki journal {inv.journal.number}.")
            return redirect("billing:invoice_detail", pk=inv.pk)

        auto_post = bool(get_int_setting("AUTO_POST_billing_INVOICE", default=0))

        try:
            with transaction.atomic():
                code = (getattr(inv.currency, "code", "") or "").upper()

                # ✅ tentukan rate final (default dari core, bisa di-override modal)
                if code == "IDR" or not code:
                    inv.exchange_rate = Decimal("1.0")
                else:
                    default_rate = get_rate_to_idr(inv.currency, inv.invoice_date)
                    if default_rate:
                        inv.exchange_rate = default_rate

                    rate_str = (request.POST.get("exchange_rate") or "").strip()
                    if rate_str:
                        try:
                            inv.exchange_rate = Decimal(rate_str)
                        except (InvalidOperation, ValueError):
                            raise ValidationError(
                                "Format exchange rate tidak valid. Gunakan titik untuk desimal, contoh 15750.25"
                            )

                    if not inv.exchange_rate or inv.exchange_rate <= 0:
                        raise ValidationError(
                            "Exchange rate wajib diisi (>0) untuk invoice non-IDR. "
                            "Isi rate di modal atau set di Core Exchange Rates."
                        )

                # ✅ audit minimal
                from django.utils import timezone
                inv.confirmed_at = timezone.now()
                inv.confirmed_by = request.user

                # confirm status + hitung idr
                inv.status = Invoice.ST_SENT
                inv.recalc_total_idr()
                inv.save(update_fields=["status", "exchange_rate", "total_idr", "confirmed_at", "confirmed_by"])

                # ✅ sesuai rule: AUTO_POST_billing_INVOICE=1 -> create+post (fungsi already post)
                if auto_post:
                    journal = create_journal_from_invoice(inv)
                    messages.success(
                        request,
                        f"Invoice {inv.number} berhasil dikonfirmasi dan journal {journal.number} telah dibuat & diposting."
                    )
                else:
                    messages.success(
                        request,
                        f"Invoice {inv.number} berhasil dikonfirmasi. (Auto Post billing Invoice: OFF → journal tidak dibuat)"
                    )

            return redirect("billing:invoice_detail", pk=inv.pk)

        except ValidationError as e:
            msg = " ".join(getattr(e, "messages", [])) or str(e)
            messages.error(request, msg)
            return redirect("billing:invoice_detail", pk=inv.pk)
