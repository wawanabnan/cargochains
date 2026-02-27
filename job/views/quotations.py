from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from job.models.quotations import Quotation, QuotationStatus
from job.forms.quotations import QuotationForm  # kalau belum ada, ganti pakai fields=[...]
from job.forms.job_orders import JobOrderForm
from django.shortcuts import render, redirect
from job.models.job_orders import JobOrder
from core.utils.numbering import get_next_number
from django.views.generic import DetailView,CreateView, UpdateView, ListView
from decimal import Decimal, InvalidOperation
from core.models.taxes import Tax
from uuid import uuid4
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import ValidationError


from django.utils import timezone
from django.db.models import Q
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from weasyprint import HTML  # pip install weasyprint
from django.utils.dateparse import parse_date
from partners.models import Customer
from core.models.services import Service
from core.models.payment_terms import PaymentTerm
from core.models.currencies import Currency
from sales.utils.signature import build_signature_context_for_quotation

import logging
import traceback
from django.db import connection

logger = logging.getLogger("cargochains.quotation_create")


def _quotation_print_context(q: Quotation):
    """
    Context untuk preview & PDF.
    Sesuaikan field yang kamu mau tampil.
    """
    jo = q.job_order  # OneToOne -> boleh None, tapi idealnya selalu ada
    return {
        "q": q,
        "jo": jo,
        # contoh: taxes M2M (kalau ada)
        "taxes": getattr(jo, "taxes", None).all() if jo and hasattr(jo, "taxes") else [],
    }

def get_queryset(self):
    qs = super().get_queryset()
    status = self.request.GET.get("status")
    today = timezone.localdate()

    if status == "EXPIRED":
        qs = qs.filter(
            Q(status=QuotationStatus.EXPIRED) |
            (Q(status__in=[QuotationStatus.DRAFT, QuotationStatus.SENT]) & Q(valid_until__lt=today))
        )
    elif status:
        qs = qs.filter(status=status)

    return qs

def _build_tax_map():
    qs = Tax.objects.filter(is_active=True).only("id", "rate", "is_withholding")
    return {
        str(t.id): {
            "rate": float(t.rate or Decimal("0")),          # percent
            "is_withholding": bool(t.is_withholding),
        }
        for t in qs
    }

class QuotationListView(LoginRequiredMixin, ListView):
    model = Quotation
    template_name = "quotations/list.html"
    context_object_name = "quotations"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Quotation.objects
            .select_related("job_order__customer", "job_order__service")
        )

        q = (self.request.GET.get("q") or "").strip()

        customer_ids = self.request.GET.getlist("customer")  # MULTI
        service_ids  = self.request.GET.getlist("service")   # MULTI
        q_statuses   = self.request.GET.getlist("q_status")  # MULTI (quotation status)

        date_from_raw = (self.request.GET.get("date_from") or "").strip()
        date_to_raw   = (self.request.GET.get("date_to") or "").strip()
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to   = parse_date(date_to_raw) if date_to_raw else None

        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(job_order__customer__name__icontains=q)
                | Q(job_order__customer__company_name__icontains=q)
                | Q(job_order__service__name__icontains=q)
                | Q(job_order__order_number__icontains=q)
                | Q(job_order__cargo_description__icontains=q)
            )

        if customer_ids:
            qs = qs.filter(job_order__customer_id__in=customer_ids)

        if service_ids:
            qs = qs.filter(job_order__service_id__in=service_ids)

        if q_statuses:
            qs = qs.filter(status__in=q_statuses)

        if date_from:
            qs = qs.filter(quote_date__gte=date_from)

        if date_to:
            qs = qs.filter(quote_date__lte=date_to)

        return qs.order_by("-quote_date", "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # keep selected values
        ctx["filter_q"] = self.request.GET.get("q", "")
        ctx["filter_customers"] = self.request.GET.getlist("customer")
        ctx["filter_services"] = self.request.GET.getlist("service")
        ctx["filter_q_statuses"] = self.request.GET.getlist("q_status")
        ctx["filter_date_from"] = self.request.GET.get("date_from", "")
        ctx["filter_date_to"] = self.request.GET.get("date_to", "")

        # dropdown data (yang punya quotation saja)
        ctx["customers"] = Customer.objects.all().order_by("name")
        ctx["services"] = Service.objects.all().order_by("name")
        ctx["payment_terms"] = PaymentTerm.objects.all().order_by("name")
        ctx["currencies"] = Currency.objects.all().order_by("name")
        
        # status quotation (sesuaikan: QuotationStatus.choices / Quotation.STATUS_CHOICES)
        ctx["quotation_status_choices"] = QuotationStatus.choices

        return ctx


class QuotationCreateView(LoginRequiredMixin, CreateView):
    model = Quotation
    form_class = QuotationForm
    template_name = "quotations/form.html"

    

    def get_context_data(self, *, qform=None, form=None):
        """
        Dipakai untuk GET pertama kali dan untuk re-render saat POST invalid.
        """
        if qform is None:
            qform = QuotationForm()
        if form is None:
            form = JobOrderForm()

        return {
            "qform": qform,   # quote_date, valid_until
            "form": form,     # JobOrderForm full fields (kecuali yang kamu nggak render di template)
            "mode": "create",
            "tax_map": _build_tax_map(),
        }

    def get_success_url(self):
        return reverse_lazy("job:quotation_list")


    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data()
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        print("scheme", request.scheme)
        print("is_secure", request.is_secure())
        print("host", request.get_host())
        print("meta proto", request.META.get("HTTP_X_FORWARDED_PROTO"))

        data = request.POST.copy()

      
        qd = (data.get("quote_date") or "").strip()
        if qd and not (data.get("job_date") or "").strip():
            data["job_date"] = qd

        print("AFTER copy quote_date:", data.get("quote_date"))
        print("AFTER copy job_date:", data.get("job_date"))


            
        qform = QuotationForm(data)
        form = JobOrderForm(data)



        if not (qform.is_valid() and form.is_valid()):
            ctx = self.get_context_data()
            ctx["qform"] = qform
            ctx["form"] = form
            return render(request, self.template_name, ctx)


        with transaction.atomic():
            # 1) create JobOrder hidden (status QUOTATION)
            job: JobOrder = form.save(commit=False)
            job.status = JobOrder.ST_QUOTATION  # hidden dari list visible :contentReference[oaicite:2]{index=2}
            job.sales_user = request.user
            # job_date: kamu bisa set sama dengan quote_date biar konsisten, tapi tidak ditampilkan
            if not job.number:
                job.number = f"TMP-{uuid4().hex[:12].upper()}"  # unik

            job.job_date = qform.cleaned_data["quote_date"]
            job.save()
            form.save_m2m()  # taxes M2M, dll

            # 2) create Quotation
            quotation = qform.save(commit=False)
            quotation.job_order = job
            quotation.status = QuotationStatus.DRAFT  # default juga boleh :contentReference[oaicite:3]{index=3}
            quotation.save()

        messages.success(request, "Quotation berhasil dibuat.",extra_tags="ui-inline") 
        return redirect(self.get_success_url())


class QuotationUpdateView(LoginRequiredMixin, UpdateView):
    model = Quotation
    template_name = "quotations/form.html"

    def get_success_url(self):
        return reverse_lazy("job:quotation_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, *, qform=None, form=None, **kwargs):
        quotation = self.object  # sudah ada di UpdateView
        if qform is None:
            qform = QuotationForm(instance=quotation)
        if form is None:
            form = JobOrderForm(instance=quotation.job_order)

        ctx = {
            "qform": qform,
            "form": form,
            "mode": "edit",
            "tax_map": _build_tax_map(),
            "object": quotation,
            "quotation": quotation,
            "job": quotation.job_order,
        }
        return ctx

    def get(self, request, *args, **kwargs):

        self.object = self.get_object()
        ctx = self.get_context_data()
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        quotation = self.object
        job = quotation.job_order

        data = request.POST.copy()

        # kalau masih mau copy quote_date -> job_date (optional)
        qd = (data.get("quote_date") or "").strip()
        if qd and not (data.get("job_date") or "").strip():
            data["job_date"] = qd

        qform = QuotationForm(data, instance=quotation)
        form = JobOrderForm(data, instance=job)

        if not (qform.is_valid() and form.is_valid()):
            ctx = self.get_context_data(qform=qform, form=form)
            return render(request, self.template_name, ctx)

        with transaction.atomic():
            form.save()   # update job order fields + m2m kalau ada
            qform.save()  # update quotation fields

        messages.success(request, "Quotation berhasil diupdate.")
        return redirect(self.get_success_url())

class QuotationStatusUpdateView(LoginRequiredMixin, View):
    """
    POST only: update status.
    Side-effect ORDERED -> JobOrder updated dilakukan oleh Quotation.save().
    """
    @transaction.atomic
    def post(self, request, pk):
        print("🔥 MASUK METHOD POST UPDATE 🔥")
        print("POST DATA:", request.POST)
        q = Quotation.objects.select_for_update().get(pk=pk)
        new_status = request.POST.get("status")

        if new_status not in QuotationStatus.values:
            messages.error(request, "Status tidak valid.")
            return redirect("job:quotation_detail", pk=pk)

        q.status = new_status
        q._sales_user = request.user  # ✅ supaya JobOrder.sales_user ikut terisi saat ORDERED
        q.save(update_fields=["status"])

        messages.success(request, "Status quotation berhasil diupdate.")
        return redirect("job:quotation_detail", pk=pk)

class QuotationDeleteView(LoginRequiredMixin, DeleteView):
    model = Quotation
    template_name = "quotations/confirm_delete.html"
    success_url = reverse_lazy("job:quotation_list")

class QuotationDetailView(DetailView):
    model = Quotation
    template_name = "quotations/detail.html"
    context_object_name = "quotation"

    def get_queryset(self):
        # load job_order biar nggak N+1
        return super().get_queryset().select_related("job_order")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        quotation = self.object
        job = quotation.job_order  # OneToOneField, bisa null :contentReference[oaicite:0]{index=0}

        qform = QuotationForm(instance=quotation)     # quote_date, valid_until :contentReference[oaicite:1]{index=1}
        jform = JobOrderForm(instance=job) if job else JobOrderForm()  # full JO fields :contentReference[oaicite:2]{index=2}

        # make read-only for detail
        for f in qform.fields.values():
            f.disabled = True
        for f in jform.fields.values():
            f.disabled = True

        ctx.update({
            "quotation": quotation,
            "job": job,
            "qform": qform,
            "form": jform,   # biar template reuse yg sama seperti JobOrder (form.html)
        })
        return ctx
    
class QuotationSendView(View):
    def post(self, request, pk):
        q = get_object_or_404(Quotation, pk=pk)

        if not request.user.has_perm("job.can_send_quotation"):
            messages.error(request, "Tidak punya akses untuk send quotation.")
            return redirect("job:quotation_detail", pk=q.id)

        try:
            q.mark_sent(request.user)
            messages.success(request, f"Quotation {q.number} berhasil di-set menjadi SENT.")
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, str(e))

        return redirect("job:quotation_detail", pk=q.id)

class QuotationConvertToOrderView2(View):
    @transaction.atomic
    def post(self, request, pk):
        q = get_object_or_404(Quotation.objects.select_for_update(), pk=pk)

        if not request.user.has_perm("job.can_convert_quotation"):
            messages.error(request, "Tidak punya akses untuk convert quotation.")
            return redirect("job:quotation_detail", pk=q.id)

        try:
            job = JobOrder.objects.select_for_update().get(pk=q.job_order_id)
            job_date = job.job_date or q.quote_date

            job.convert_from_quotation(user=request.user, job_date=job_date)
            q.mark_ordered(request.user)

            messages.success(request, f"Quotation {q.number} berhasil di-convert menjadi Order.")
            return redirect("job:joborder_detail", pk=job.id)

        except Exception as e:
            messages.error(request, str(e))
            return redirect("job:quotation_detail", pk=q.id)

class QuotationPrintPreviewView(LoginRequiredMixin, DetailView):
    model = Quotation
    template_name = "quotations/quote_print_preview.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_quotation_print_context(self.object))
        profile = getattr(self.request.user, "profile", None)
        ctx.setdefault("signature_name", (self.request.user.get_full_name() or self.request.user.username))
        ctx.setdefault("signature_title", getattr(profile, "title", "") if profile else "")
        ctx.setdefault("signature_image", getattr(profile, "signature", None) if profile else None)

        return ctx

class QuotationPDFView(LoginRequiredMixin, View):
    def get(self, request, pk: int, *args, **kwargs):
        quotation = get_object_or_404(Quotation, pk=pk)

        # ambil context existing
        ctx = _quotation_print_context(quotation) or {}

        # ✅ pastikan template selalu punya object penting (anti "debug kosong")
        ctx.setdefault("quotation", quotation)
        ctx.setdefault("q", quotation)  # optional alias kalau template ada pakai q
        ctx.setdefault("job", quotation.job_order)
        ctx.setdefault("job_order", quotation.job_order)
        profile = getattr(request.user, "profile", None)
        ctx.setdefault("signature_name", (request.user.get_full_name() or request.user.username))
        ctx.setdefault("signature_title", getattr(profile, "title", "") if profile else "")
        ctx.setdefault("signature_image", getattr(profile, "signature", None) if profile else None)

        html = render_to_string("quotations/quote_pdf.html", ctx, request=request)

        base_url = request.build_absolute_uri("/")
        pdf_bytes = HTML(string=html, base_url=base_url).write_pdf()

        filename = f"quotation-{(quotation.number or str(pk)).replace('/', '-')}.pdf"
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        return resp

class QuotationConvertToOrderView(View):
    @transaction.atomic
    def post(self, request, pk):
        q = get_object_or_404(
            Quotation._base_manager.select_for_update(),
            pk=pk
        )

        if not request.user.has_perm("job.can_convert_quotation"):
            messages.error(
                request,
                "Tidak punya akses untuk convert quotation.",
                extra_tags="ui-modal",
            )
            return redirect("job:quotation_detail", pk=q.id)

        # idempotent: kalau sudah pernah ordered, jangan generate nomor lagi
        if getattr(q, "status", None) == "ORDERED":  # kalau ada konstanta: Quotation.ST_ORDERED
            messages.success(
                request,
                f"Quotation {q.number} sudah pernah di-convert.",
                extra_tags="ui-modal",
            )
            return redirect("job:job_order_detail", pk=q.job_order_id)

        try:
            job = JobOrder.objects.select_for_update().get(pk=q.job_order_id)
            job_date = job.job_date or q.quote_date

            job.convert_from_quotation(user=request.user, job_date=job_date)
            q.mark_ordered(request.user)

            messages.success(
                request,
                f"Quotation {q.number} berhasil di-convert menjadi Order.",
                extra_tags="ui-modal",
            )
            return redirect("job:job_order_detail", pk=job.id)

        except Exception as e:
            messages.error(
                request,
                f"{type(e).__name__}: {e}",
                extra_tags="ui-modal",
            )
            return redirect("job:quotation_detail", pk=q.id)




ALLOWED_DELETE_STATUSES = ("DRAFT", "CANCELLED", "EXPIRED")

class QuotationDeleteView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        ids_raw = (request.POST.get("ids") or "").split(",")
        ids = [i for i in ids_raw if i.strip().isdigit()]

        if not ids:
            messages.error(request, "Tidak ada data yang dipilih.")
            return redirect("job:quotation_list")

        qs = Quotation.objects.filter(pk__in=ids)

        # Boleh delete hanya yang status dalam ALLOWED_DELETE_STATUSES
        deletable = qs.filter(status__in=ALLOWED_DELETE_STATUSES)
        blocked = qs.exclude(status__in=ALLOWED_DELETE_STATUSES)

        deleted_count = deletable.count()
        blocked_count = blocked.count()

        if deleted_count:
            deletable.delete()
            messages.success(
                request,
                f"{deleted_count} quotation (Draft/Cancelled/Expired) berhasil dihapus.",
            )

        if blocked_count:
            messages.warning(
                request,
                f"{blocked_count} quotation tidak bisa dihapus (status bukan Draft/Cancelled/Expired).",
            )

        if not deleted_count and not blocked_count:
            messages.info(request, "Tidak ada quotation yang dihapus.")

        return redirect("job:quotation_list")


