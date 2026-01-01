# sales/views/invoices.py
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

from sales.job_order_model import JobOrder
from sales.invoice_model import Invoice, InvoiceLine
from sales.forms.invoices import InvoiceForm, InvoiceLineFormSet
from sales.utils.invoices import build_invoice_description_from_job
from decimal import Decimal, ROUND_HALF_UP
from core.models.taxes import Tax
from sales.utils.permissions import is_finance
from django.core.exceptions import PermissionDenied
from accounting.services.invoice_posting import create_journal_from_invoice
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from accounting.services.invoice_posting import create_journal_from_invoice  # sesuaikan path import

from django.core.exceptions import PermissionDenied


# =========================================================
# Helpers
# =========================================================
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
        inv.status = "UNPAID"

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
    invoice.save(update_fields=["subtotal_amount", "tax_amount", "total_amount"])

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
    template_name = "invoices/list.html"
    context_object_name = "invoices"
    paginate_by = 12

    def get_queryset(self):
        
        qs = (
            Invoice.objects
            .all()
            .select_related("customer")   # kalau field customer ada
            .order_by("-created_at")
        )
        return qs

    
class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "invoices/detail.html"
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

        if self.request.method == "POST":
            ctx["formset"] = InvoiceLineFormSet(self.request.POST)

        else:
            fs = InvoiceLineFormSet()

            if fs.forms:
                price_key = "price"

                # basis harga: subtotal (sebelum tax)
                base_amount = getattr(self.job, "subtotal_amount", None)
                if base_amount is None:
                    base_amount = getattr(self.job, "total_amount", 0) or 0

                fs.forms[0].initial = {
                    "description": build_invoice_description_from_job(self.job),
                    "quantity": 1,
                    price_key: base_amount,
                }

                # ✅ AUTO-CENTANG TAX PPN 1.1% (seolah klik checkbox)
                ppn11 = get_ppn_11_tax()
                if ppn11 and "taxes" in fs.forms[0].fields:
                    fs.forms[0].initial["taxes"] = [ppn11.pk]

            ctx["formset"] = fs
        inv = ctx["invoice"]  
        ctx["mode"] = "from_job"
        ctx["job_order"] = self.job
        ctx["can_confirm"] = inv.can_confirm(self.request.user)
        #ctx["can_confirm"] = self.object.can_confirm(self.request.user)
        return ctx
    
class InvoiceCreateManualView(LoginRequiredMixin, View):
    template_name = "invoices/form.html"

    def get(self, request):
        form = InvoiceForm()
        formset = InvoiceLineFormSet()
        return render(request, self.template_name, {"form": form, "formset": formset, "mode": "manual"})

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
            return redirect("sales:invoice_detail", pk=inv.pk)


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
                {"form": form, "formset": formset, "mode": "manual"}
            )


        return render(request, self.template_name, {"form": form, "formset": formset, "mode": "manual"})

    def get(self, request):
        form = InvoiceForm()
        formset = InvoiceLineFormSet()

        messages.info(request, f"FORMSET form class: {formset.form.__name__}")

        return render(request, self.template_name, {"form": form, "formset": formset, "mode": "manual"})

class InvoiceDeleteView(LoginRequiredMixin, View):
    template_name = "sales/invoice_confirm_delete.html"

    def get(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)
        return render(request, self.template_name, {"invoice": inv})

    @transaction.atomic
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)
        inv.delete()
        messages.success(request, "Invoice berhasil dihapus.")
        return redirect("sales:invoice_list")

class InvoiceCreateFromJobOrder2View(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.job = get_object_or_404(JobOrder, pk=kwargs["job_order_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        job = self.job
        initial = super().get_initial()
        initial.update({
            "job_order": job,
            "invoice_date": timezone.now().date(),
            "due_date": timezone.now().date(),
        })
        if hasattr(Invoice, "customer") and getattr(job, "customer_id", None):
            initial["customer"] = job.customer_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            ctx["formset"] = InvoiceLineFormSet(self.request.POST)
        else:
            fs = InvoiceLineFormSet()
            if fs.forms:
                price_key = "price"

                # ✅ basis harga: subtotal (sebelum tax), fallback aman
                base_amount = getattr(self.job, "subtotal_amount", None)
                if base_amount is None:
                    base_amount = getattr(self.job, "total_amount", 0) or 0

                fs.forms[0].initial = {
                    "description": build_invoice_description_from_job(self.job),
                    "quantity": 1,
                    price_key: base_amount,  # ✅ FIX: jangan pakai total langsung
                }
   
        ctx["formset"] = fs

        ctx["mode"] = "from_job"
        ctx["job_order"] = self.job
        return ctx


    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]

        if not formset.is_valid():
            return self.form_invalid(form)

        inv = form.save(commit=False)
        inv.job_order = self.job

        if hasattr(inv, "created_by_id") and not getattr(inv, "created_by_id", None):
            inv.created_by = self.request.user
        if hasattr(inv, "updated_by_id"):
            inv.updated_by = self.request.user

        if hasattr(inv, "customer_id") and getattr(self.job, "customer_id", None):
            inv.customer_id = self.job.customer_id

        inv.save()

        formset.instance = inv
        formset.save()

        ppn11 = get_ppn_11_tax()

        if ppn11:
            for ln in inv.lines.all():
                # ✅ seolah klik checkbox PPN: tambahkan tanpa menghapus tax lain
                ln.taxes.add(ppn11)
        else:
            messages.warning(
                self.request,
                "Master Tax PPN 1.1% belum tersedia. Pajak pada invoice line kosong."
            )

        # ✅ recalc dari line (PPN sudah di line)
        recalc_invoice_totals(inv)


        messages.success(self.request, "Invoice berhasil dibuat dari Job Order.")
        return redirect("sales:invoice_detail", pk=inv.pk)
class InvoiceCreateFromJobOrder3View(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.job = get_object_or_404(JobOrder, pk=kwargs["job_order_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        job = self.job
        initial = super().get_initial()
        today = timezone.localdate()
        initial.update({
            "job_order": job,
            "invoice_date": today,
            "due_date": today,
        })
        if hasattr(Invoice, "customer") and getattr(job, "customer_id", None):
            initial["customer"] = job.customer_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        if self.request.method == "POST":
            ctx["formset"] = InvoiceLineFormSet(self.request.POST)
        else:
            fs = InvoiceLineFormSet()
            if fs.forms:
                f0 = fs.forms[0]
                price_key = "price"

                # ✅ basis harga: subtotal (sebelum tax), fallback kalau belum ada
                base_amount = getattr(self.job, "subtotal_amount", None)
                if base_amount is None:
                    base_amount = getattr(self.job, "total_amount", 0) or 0

                f0.initial = {
                    "description": build_invoice_description_from_job(self.job),
                    "quantity": 1,
                    price_key: base_amount,
                }

                # ✅ pajak: murni dari flag job.is_tax (bukan job.tax_amount)
                if getattr(self.job, "is_tax", False) and "taxes" in f0.fields:
                    ppn11 = get_ppn_11_tax()
                    if ppn11:
                        # auto-centang checkbox tax (UX)
                        f0.fields["taxes"].initial = [ppn11]
                    else:
                        messages.warning(
                            self.request,
                            "Master Tax PPN 1.1% belum tersedia. Pajak pada invoice line kosong."
                        )

            ctx["formset"] = fs

        ctx["mode"] = "from_job"
        ctx["job_order"] = self.job
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]

        if not formset.is_valid():
            return self.form_invalid(form)

        inv = form.save(commit=False)
        inv.job_order = self.job

        if hasattr(inv, "created_by_id") and not getattr(inv, "created_by_id", None):
            inv.created_by = self.request.user
        if hasattr(inv, "updated_by_id"):
            inv.updated_by = self.request.user

        if hasattr(inv, "customer_id") and getattr(self.job, "customer_id", None):
            inv.customer_id = self.job.customer_id

        inv.save()

        formset.instance = inv
        formset.save()

        # ✅ fallback: kalau job taxable tapi user/POST tidak mengirim taxes, auto add PPN
        if getattr(self.job, "is_tax", False):
            ppn11 = get_ppn_11_tax()
            if ppn11:
                for ln in inv.lines.all():
                    if not ln.taxes.exists():
                        ln.taxes.add(ppn11)
            else:
                messages.warning(
                    self.request,
                    "Master Tax PPN 1.1% belum tersedia. Pajak pada invoice line kosong."
                )

        # ✅ recalc dari line (pajak dihitung dari ln.taxes)
        recalc_invoice_totals(inv)

        messages.success(self.request, "Invoice berhasil dibuat dari Job Order.")
        return redirect("sales:invoice_detail", pk=inv.pk)

class InvoiceMarkPaidView(LoginRequiredMixin, View):
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)
        inv.amount_paid = inv.total_amount
        invoice_refresh_payment_status(inv, save=False)
        inv.save(update_fields=["amount_paid", "status"])

        messages.success(request, "Invoice ditandai PAID.")
        return redirect("sales:invoice_detail", pk=inv.pk)


@login_required
@transaction.atomic
def generate_invoice_from_job(request, job_order_id):
    if request.method != "POST":
        messages.error(request, "Aksi tidak valid.")
        return redirect("sales:job_order_detail", pk=job_order_id)

    job = get_object_or_404(JobOrder, pk=job_order_id)

    if job.is_invoiced and job.invoices.exists():
        inv = job.invoices.order_by("-id").first()
        messages.warning(request, f"Job {job.number} sudah pernah dibuat invoice.")
        return redirect("sales:invoice_detail", pk=inv.pk)

    inv = Invoice.objects.create(
        job_order=job,
        invoice_date=job.job_date,
        due_date=job.job_date,
        status=getattr(Invoice, "STATUS_UNPAID", "UNPAID"),
        subtotal_amount=job.total_amount or 0,
        tax_amount=job.tax_amount or 0,
        total_amount=getattr(job, "grand_total", None) or ((job.total_amount or 0) + (job.tax_amount or 0)),
        notes_customer="",
        notes_internal=f"Generated from JobOrder {job.number}",
        customer_id=getattr(job, "customer_id", None),
    )

    desc_main = (job.cargo_description or "").strip() or f"Job Order {job.number}"
    desc_route = " / ".join([x for x in [
        job.pickup.strip() if getattr(job, "pickup", None) else "",
        job.delivery.strip() if getattr(job, "delivery", None) else "",
    ] if x])
    description = desc_main if not desc_route else f"{desc_main}\n{desc_route}"

    line_kwargs = dict(
        invoice=inv,
        description=description,
        quantity=getattr(job, "quantity", None) or 1,
    )
    price_field = _line_price_field_name()
    line_kwargs[price_field] = job.total_amount or 0

    InvoiceLine.objects.create(**line_kwargs)

    job.is_invoiced = True
    job.save(update_fields=["is_invoiced"])

    recalc_invoice_totals(inv)

    messages.success(request, f"Invoice {inv.number} berhasil dibuat dari Job {job.number}.")
    return redirect("sales:invoice_detail", pk=inv.pk)


class InvoiceChangeStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)

        from sales.utils.permissions import is_finance
        if not is_finance(request.user):
            raise PermissionDenied("Hanya Finance yang boleh ubah status invoice.")

        inv.status = request.POST.get("status", inv.status)
        if hasattr(inv, "updated_by_id"):
            inv.updated_by = request.user
        inv.save(update_fields=["status", "updated_by"] if hasattr(inv, "updated_by_id") else ["status"])

        return redirect("sales:invoice_detail", pk=inv.pk)


class InvoiceMarkPaidView(View):
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)

        if not inv.can_mark_paid(request.user):
            raise PermissionDenied

        inv.status = Invoice.ST_PAID
        inv.save(update_fields=["status"])
        return redirect("sales:invoice_detail", pk=inv.pk)

class InvoiceCreateFromJobOrderView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.job = get_object_or_404(JobOrder, pk=kwargs["job_order_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        today = timezone.localdate()
        initial.update({
            "job_order": self.job,
            "invoice_date": today,
            "due_date": today,
        })
        if hasattr(Invoice, "customer") and getattr(self.job, "customer_id", None):
            initial["customer"] = self.job.customer_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        if self.request.method == "POST":
            ctx["formset"] = InvoiceLineFormSet(self.request.POST)
        else:
            fs = InvoiceLineFormSet()
            if fs.forms:
                f0 = fs.forms[0]
                price_key = "price"

                # ✅ basis harga: subtotal job (sebelum tax)
                base_amount = getattr(self.job, "subtotal_amount", None)
                if base_amount is None:
                    base_amount = getattr(self.job, "total_amount", 0) or 0

                f0.initial = {
                    "description": build_invoice_description_from_job(self.job),
                    "quantity": 1,
                    price_key: base_amount,
                }

                # ✅ UX: kalau job taxable, centang tax di UI (master id=2)
                if getattr(self.job, "is_tax", False) and "taxes" in f0.fields:
                    try:
                        ppn = Tax.objects.get(pk=2)
                        f0.fields["taxes"].initial = [ppn]
                    except Tax.DoesNotExist:
                        messages.warning(self.request, "Master Tax PPN (id=2) tidak ditemukan.")

            ctx["formset"] = fs

        ctx["mode"] = "from_job"
        ctx["job_order"] = self.job
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]

        if not formset.is_valid():
            return self.form_invalid(form)

        # 1) Save header
        inv = form.save(commit=False)
        inv.job_order = self.job

        if hasattr(inv, "created_by_id") and not getattr(inv, "created_by_id", None):
            inv.created_by = self.request.user
        if hasattr(inv, "updated_by_id"):
            inv.updated_by = self.request.user
        if hasattr(inv, "customer_id") and getattr(self.job, "customer_id", None):
            inv.customer_id = self.job.customer_id

        inv.save()

        # 2) Save lines
        formset.instance = inv
        lines = formset.save(commit=False)
        for ln in lines:
            # pastikan FK ke invoice benar (umumnya invoice)
            if hasattr(ln, "invoice_id"):
                ln.invoice_id = inv.pk
            ln.save()

        for obj in formset.deleted_objects:
            obj.delete()

        # simpan m2m lain dari formset (kalau ada)
        formset.save_m2m()

        # =========================================================
        # 3) ✅ PAKSA: setiap line punya tax id=2 (tulis langsung through table)
        # =========================================================
        if getattr(self.job, "is_tax", False):
            sample = inv.lines.first()
            if not sample or not hasattr(sample, "taxes"):
                messages.warning(self.request, "InvoiceLine tidak punya field M2M 'taxes'.")
                return redirect("sales:invoice_detail", pk=inv.pk)

            TaxModel = sample.taxes.model
            Through = sample.taxes.through  # tabel M2M

            # cari field FK ke InvoiceLine & ke TaxModel pada through model
            line_fk_name = None
            tax_fk_name = None
            for f in Through._meta.fields:
                # ForeignKey ke line model
                if getattr(f, "remote_field", None) and f.remote_field and f.remote_field.model == sample.__class__:
                    line_fk_name = f.name
                # ForeignKey ke tax model
                if getattr(f, "remote_field", None) and f.remote_field and f.remote_field.model == TaxModel:
                    tax_fk_name = f.name

            if not line_fk_name or not tax_fk_name:
                messages.warning(self.request, "Through table taxes tidak standard (FK tidak terdeteksi).")
                return redirect("sales:invoice_detail", pk=inv.pk)

            try:
                ppn = TaxModel.objects.get(pk=2)
            except TaxModel.DoesNotExist:
                messages.warning(self.request, "Master Tax id=2 tidak ditemukan.")
                return redirect("sales:invoice_detail", pk=inv.pk)

            line_ids = list(inv.lines.values_list("id", flat=True))
            if line_ids:
                # hapus dulu relasi tax lama (biar benar-benar pasti)
                Through.objects.filter(**{f"{line_fk_name}__in": line_ids}).delete()

                # insert relasi tax id=2 untuk semua line
                objs = [Through(**{line_fk_name: ln_id, tax_fk_name: ppn.pk}) for ln_id in line_ids]
                Through.objects.bulk_create(objs)

        # =========================================================

        messages.success(self.request, "Invoice berhasil dibuat dari Job Order.")
        return redirect("sales:invoice_detail", pk=inv.pk)


class InvoiceConfirmView2(View):
    def post(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)

        if not inv.can_confirm(request.user):
            raise PermissionDenied


        # 2️⃣ idempotent guard (anti double journal)
        if inv.journal_id:
            messages.info(
                request,
                f"Invoice {inv.number} sudah memiliki journal {inv.journal.number}."
            )
            return redirect("sales:invoice_detail", pk=inv.pk)

        try:
            with transaction.atomic():
                # 3️⃣ ubah status invoice
                inv.status = Invoice.ST_SENT
                inv.save(update_fields=["status"])

                # 4️⃣ 🔥 AUTO CREATE + POST JOURNAL
                journal = create_journal_from_invoice(inv)

            messages.success(
                request,
                f"Invoice {inv.number} berhasil dikonfirmasi "
                f"dan journal {journal.number} telah dibuat."
            )

        except ValidationError as e:
            messages.error(request, f"Gagal membuat journal: {e}")

        return redirect("sales:invoice_detail", pk=inv.pk)




class InvoiceUpdateView(LoginRequiredMixin, View):
    template_name = "invoices/form.html"

    def get(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)

        form = InvoiceForm(instance=inv)
        formset = InvoiceLineFormSet(instance=inv)
        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "mode": "edit", "invoice": inv},
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
            return redirect("sales:invoice_detail", pk=inv.pk)

        messages.error(request, "VALIDATION ERROR — cek detail di bawah.")
        messages.error(request, f"HEADER(form) errors:\n{form.errors.as_text()}")
        messages.error(request, f"LINE(formset) non_form_errors:\n{formset.non_form_errors()}")
        messages.error(request, f"LINE(formset) errors:\n{formset.errors}")

        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "mode": "edit", "invoice": inv},
        )




from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from core.models.settings import CoreSetting  # sesuaikan nama model core settings om
from sales.models import Invoice
from accounting.services.invoice_posting import create_journal_from_invoice  # sesuai om


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
            return redirect("sales:invoice_detail", pk=inv.pk)

        auto_post = bool(get_int_setting("AUTO_POST_SALES_INVOICE", default=0))

        try:
            with transaction.atomic():
                # confirm status
                inv.status = Invoice.ST_SENT
                inv.save(update_fields=["status"])

                # auto post journal?
                if auto_post:
                    journal = create_journal_from_invoice(inv)
                    messages.success(
                        request,
                        f"Invoice {inv.number} berhasil dikonfirmasi dan journal {journal.number} telah dibuat."
                    )
                else:
                    messages.success(
                        request,
                        f"Invoice {inv.number} berhasil dikonfirmasi. (Auto Post Sales Invoice: OFF)"
                    )

            return redirect("sales:invoice_detail", pk=inv.pk)

        except ValidationError as e:
            # rollback otomatis karena atomic()
            msg = " ".join(getattr(e, "messages", [])) or str(e)
            messages.error(request, msg)
            return redirect("sales:invoice_detail", pk=inv.pk)
