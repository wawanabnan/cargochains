from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from job.models.job_orders import JobOrder,JobOrderAttachment
from job.models.job_costs import JobCost,JobCostType


from job.forms.job_orders   import JobOrderForm 
from job.forms.Job_costs import JobCostFormSet

from job.forms.attachment  import JobOrderAttachmentForm
from django.views.generic import ListView

from partners.models import Customer
from core.models.services import Service
from core.models.currencies import Currency
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from core.utils.numbering import get_next_number
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseBadRequest
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError


from billing.models.customer_invoice import   Invoice, InvoiceLine
from billing.utils.invoices import generate_invoice_from_job
from django.db.models import Sum
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from job.models.job_orders import JobOrder
from job.forms.job_orders import JobOrderForm
from job.forms.Job_costs import JobCostForm, JobCostFormSet
from job.utils.messages import JobMessages
from django.utils.safestring import mark_safe
from core.models.taxes import Tax
import json
from django.db.models import Q


def cost_type_meta_json():
    qs = JobCostType.objects.filter(is_active=True).only("id", "requires_vendor", "cost_group")
    meta = {
        str(ct.id): {
            "requires_vendor": int(bool(ct.requires_vendor)),
            "cost_group": (ct.cost_group or ""),
        }
        for ct in qs
    }
    return mark_safe(json.dumps(meta))


# ==========================
# LIST
# ==========================
class JobOrderListView(LoginRequiredMixin, ListView):
    model = JobOrder
    template_name = "job_order/list.html"
    context_object_name = "job_orders"
    paginate_by = 19

    def get_queryset(self):
        qs = (
            JobOrder.objects.visible()
            .select_related("customer", "service", "payment_term", "currency", "sales_user")
        )

        # ===== sorting =====
        sort = (self.request.GET.get("sort") or "-job_date").strip()
        allowed = {
            "number", "-number",
            "job_date", "-job_date",
            "customer__name", "-customer__name",
            "grand_total", "-grand_total",
            "status", "-status",
        }
        if sort not in allowed:
            sort = "-job_date"

        # ===== filters =====
        q = (self.request.GET.get("q") or "").strip()
        customer_id = (self.request.GET.get("customer") or "").strip()
        service_id = (self.request.GET.get("service") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        date_from = (self.request.GET.get("date_from") or "").strip()
        date_to = (self.request.GET.get("date_to") or "").strip()

        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(order_number__icontains=q)
                | Q(cargo_description__icontains=q)
                | Q(customer__name__icontains=q)
                | Q(service__name__icontains=q)
            )

        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        if service_id:
            qs = qs.filter(service_id=service_id)

        if status:
            qs = qs.filter(status=status)

        if date_from:
            qs = qs.filter(job_date__gte=date_from)

        if date_to:
            qs = qs.filter(job_date__lte=date_to)

        # final ordering
        return qs.order_by(sort, "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # nilai filter agar dropdown tetap selected
        ctx["filter_q"] = self.request.GET.get("q", "")
        ctx["filter_customer"] = self.request.GET.get("customer", "")
        ctx["filter_service"] = self.request.GET.get("service", "")
        ctx["filter_status"] = self.request.GET.get("status", "")
        ctx["filter_date_from"] = self.request.GET.get("date_from", "")
        ctx["filter_date_to"] = self.request.GET.get("date_to", "")

        # dropdown data
        ctx["customers"] = Customer.objects.all().order_by("name")
        ctx["services"] = Service.objects.all().order_by("name")
        ctx["status_choices"] = JobOrder.STATUS_CHOICES

        # sort current (buat header sort link)
        ctx["sort"] = (self.request.GET.get("sort") or "-job_date").strip()

        return ctx

# ==========================
# CREATE
# ==========================

class JobOrderCreateView(LoginRequiredMixin, View):
    template_name = "job_order/form.html"

    def get(self, request):
        form = JobOrderForm()
        return render(request, self.template_name, {
            "form": form,
            "job": None,
            "cost_formset": None,
            "tax_map": _build_tax_map(),
             'is_update': False
        })

    def post(self, request):
        data = request.POST.copy()

        currency_id = data.get("currency")
        if currency_id:
            cur = Currency.objects.filter(pk=currency_id).only("code").first()
            code = (cur.code or "").upper() if cur else ""

            if code == "IDR":
                data["kurs_idr"] = "1"
            else:
                raw = (data.get("kurs_idr") or "").strip()
                if raw:
                    raw = raw.replace(" ", "").replace(".", "").replace(",", ".")
                    data["kurs_idr"] = raw

        # ✅ penting: include FILES
        form = JobOrderForm(data, request.FILES)

        if not form.is_valid():
            messages.error(request, "Form tidak valid, silakan diperiksa kembali.")
            return render(request, self.template_name, {
                "form": form,
                "job": None,
                "cost_formset": None,
                "tax_map": _build_tax_map(),  
                "is_update": False, 
            })

        job = form.save(commit=False)
        job.sales_user = request.user
        job.status = JobOrder.ST_DRAFT

        if job.currency and (job.currency.code or "").upper() == "IDR":
            job.kurs_idr = Decimal("1.00")

        job.save()

        # ✅ WAJIB untuk M2M (taxes)
        form.save_m2m()

        messages.success(request, "Job Order has been created.")
        # ✅ redirect bener: ke detail (atau list tanpa pk)
        return redirect("job:job_order_detail", pk=job.pk)
        # atau kalau memang mau list:
        # return redirect("job:job_order_list")


# ==========================
# UPDATE
# ==========================

class JobOrderUpdateView(LoginRequiredMixin, View):
    template_name = "job_order/form.html"

    def get_object(self, pk):
        return get_object_or_404(JobOrder, pk=pk)

    def get(self, request, pk):
        job = self.get_object(pk)
        form = JobOrderForm(instance=job)

        return render(request, self.template_name, {
            "form": form,
            "job": job,
            "tax_map": _build_tax_map(),
        })

    def post(self, request, pk):
        job = self.get_object(pk)        
        form = JobOrderForm(request.POST, request.FILES, instance=job)

        if not form.is_valid():
            messages.error(request, "Form Job Order belum benar, silakan dicek lagi.", extra_tags="ui-modal")
            return render(request, self.template_name, {
                "form": form,
                "job": job,
                "tax_map": _build_tax_map(),
            })

        try:
            with transaction.atomic():
                job_obj = form.save(commit=False)
                if not job_obj.sales_user_id:
                    job_obj.sales_user = request.user
                job_obj.save()
                form.save_m2m()

            messages.success(request, "Job Order berhasil diupdate.", extra_tags="ui-modal")
            return redirect("job:job_order_detail", pk=job_obj.pk)

        except Exception as e:
            messages.error(request, f"Gagal menyimpan: {type(e).__name__}: {e}", extra_tags="ui-modal")
            return render(request, self.template_name, {
                "form": form,
                "job": job,
                "tax_map": _build_tax_map(),
            })



# ==========================
# DETAIL
# ==========================
from django.db.models import Sum
from job.reports.services import ProfitabilityService

class JobOrderDetailView(LoginRequiredMixin, DetailView):
    model = JobOrder
    template_name = "job_order/detail.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = self.object

        # Cost lines
        costs = JobCost.objects.filter(job_order=job, is_active=True).order_by("id")

        # Totals (sesuai workflow)
        est_total = costs.aggregate(total=Sum("est_amount"))["total"] or 0
        act_total = costs.aggregate(total=Sum("actual_amount"))["total"] or 0

        # sebelum complete → pakai estimasi, setelah complete → pakai actual
        total_cost = act_total if job.status == JobOrder.ST_COMPLETED else est_total

        ctx["costs"] = costs
        ctx["est_total_cost"] = est_total
        ctx["actual_total_cost"] = act_total
        ctx["total_cost"] = total_cost

        # Formset edit cost di detail
        ctx["cost_formset"] = JobCostFormSet(instance=job)

        # Attachments
        ctx["attachment"] =  job.job_order_attachments.all()
        ctx["attachment_form"] = JobOrderAttachmentForm()
        ctx["cost_type_meta_json"] = cost_type_meta_json()

        svc = ProfitabilityService(revenue_field="amount")  # sesuaikan
        ctx["profit"] = svc.build_for_job(job)
        


        return ctx

from django.http import JsonResponse


from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404

class JobOrderAttachmentUploadView(LoginRequiredMixin, View):

    def post(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)

        file = request.FILES.get("file")
        description = request.POST.get("description", "")

        if not file:
            return JsonResponse({
                "success": False,
                "error": "File tidak ditemukan"
            }, status=400)

        att = JobOrderAttachment.objects.create(
            job_order=job,
            file=file,
            description=description,
            uploaded_by=request.user
        )

        return JsonResponse({
            "success": True,
            "id": att.pk
        })
    

class JobOrderAttachmentDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk, att_id):
        job = get_object_or_404(JobOrder, pk=pk)
        att = get_object_or_404(JobOrderAttachment, pk=att_id, job_order=job)

        att.file.delete(save=False)
        att.delete()

        return JsonResponse({"success": True})
    
    
class JobOrderBulkStatusView(LoginRequiredMixin, View):
    def post(self, request):
        action = request.POST.get("action")
        ids = request.POST.getlist("ids[]")

        if not ids:
            messages.info(request, "Tidak ada Job Order yang dipilih.")
            return redirect("job:job_order_list")

        qs = JobOrder.objects.filter(pk__in=ids).exclude(status=JobOrder.ST_COMPLETED)

        if action == "pending":
            updated = qs.filter(status=JobOrder.ST_IN_PROGRESS).update(status=JobOrder.ST_PENDING)
            messages.success(request, f"{updated} Job Order berhasil di-set Pending.")

        elif action == "cancel":
            updated = qs.exclude(status=JobOrder.ST_CANCELLED).update(status=JobOrder.ST_CANCELLED)
            messages.warning(request, f"{updated} Job Order berhasil di-cancel.")

        else:
            messages.error(request, "Action tidak valid.")

        return redirect("job:job_order_list")



from django.http import JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction



class JobOrderCostsUpdateView(LoginRequiredMixin, View):

    
    def post(self, request, pk):

        job = get_object_or_404(JobOrder, pk=pk)

        if job.status in {
                JobOrder.ST_IN_PROGRESS,
                JobOrder.ST_COMPLETED,
                JobOrder.ST_CANCELLED,
            }:
            is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
            msg = "Job Cost terkunci saat status IN PROGRESS."

            if is_ajax:
                return JsonResponse({
                    "ok": False,
                    "ajax": True,
                    "message": msg,
                }, status=403)

            messages.error(request, msg)
            return redirect("job:job_order_detail", pk=job.pk)


        formset = JobCostFormSet(request.POST, instance=job)
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        # ==================================================
        # ✅ FINAL RULE:
        # kalau user TIDAK menyentuh apa pun → JANGAN validasi
        # ==================================================
        touched = request.POST.get("jobcost_touched") == "1"

        if not touched:
            if is_ajax:
                html = render_to_string(
                    "job_order/extension/_cost_detail.html",
                    {
                        "job": job,
                        "cost_formset": JobCostFormSet(instance=job),
                        "cost_type_meta_json": cost_type_meta_json(),
                    },
                    request=request,
                )
                return JsonResponse({
                    "ok": True,
                    "ajax": True,
                    "message": "Tidak ada perubahan.",
                    "html": html,
                    "debug": {"touched": False},
                })

            messages.info(request, "Tidak ada perubahan pada Job Cost.")
            return redirect("job:job_order_detail", pk=job.pk)

        # ==================================================
        # ⬇️ BARU DI SINI VALIDASI KETAT
        # ==================================================
        print("DESC required:", formset.forms[-1].fields["description"].required)
        print("DESC model blank:", formset.forms[-1]._meta.model._meta.get_field("description").blank)
        print("DESC posted:", repr(formset.forms[-1].data.get("job_order_costs-6-description")))

        if not formset.is_valid():

            # ==================================================
            # ✅ INJECT class "is-invalid" utk field yang error
            # (biar border merah muncul di UI)
            # ==================================================
            for f in formset.forms:
                if not f.errors:
                    continue
                for name in f.errors.keys():
                    field = f.fields.get(name)
                    if not field:
                        continue
                    css = field.widget.attrs.get("class", "")
                    if "is-invalid" not in css:
                        field.widget.attrs["class"] = (css + " is-invalid").strip()
            # ==================================================

            debug = {
                "non_form_errors": formset.non_form_errors(),
                "forms": [f.errors for f in formset.forms],
            }

            if is_ajax:
                html = render_to_string(
                    "job_order/extension/_cost_detail.html",
                    {
                        "job": job,
                        "cost_formset": formset,
                        "cost_type_meta_json": cost_type_meta_json(),
                        "cost_locked": job.is_cost_locked, 
                    },
                    request=request,
                )
                return JsonResponse({
                    "ok": False,
                    "ajax": True,
                    "message": "Ada error input. Cek field merah.",
                    "html": html,
                    "debug": debug,
                }, status=400)

            messages.error(request, "Ada error input pada Job Cost.")
            return redirect("job:job_order_detail", pk=job.pk)

        # ==================================================
        # ✅ SAVE (karena touched + valid)
        # ==================================================
        with transaction.atomic():
            instances = formset.save(commit=False)

            # SAVE/UPDATE yang ada di formset
            for obj in instances:
            #    ct = obj.cost_type  # JobCostType instance
            #    obj.uom_id = ct.uom_id   # ✅ copy FK id (anti string)
                obj.save()

            # DELETE rows yang ditandai
            for obj in formset.deleted_objects:
                obj.delete()

            formset.save_m2m()

        if is_ajax:
            fresh_formset = JobCostFormSet(instance=job)
            html = render_to_string(
                "job_order/extension/_cost_detail.html",
                {
                    "job": job,
                    "cost_formset": fresh_formset,
                    "cost_type_meta_json": cost_type_meta_json(),
                    "cost_locked": job.is_cost_locked,
                },
                request=request,
            )
            return JsonResponse({
                "ok": True,
                "ajax": True,
                "message": "Tersimpan ✅. Silakan lanjut input cost.",
                "html": html,
            })

        messages.success(request, "Job Cost tersimpan.")
        return redirect("job:job_order_detail", pk=job.pk)

    

def _build_tax_map():
    qs = Tax.objects.filter(is_active=True).only("id", "rate", "is_withholding")
    return {
        str(t.id): {
            "rate": float(t.rate or Decimal("0")),          # percent
            "is_withholding": bool(t.is_withholding),
        }
        for t in qs
    }


class JobOrderGenerateInvoiceView(LoginRequiredMixin, View):
    def post(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)

        invoice = generate_invoice_from_job(job)

        messages.success(
            request,
            f"Invoice {invoice.number} berhasil dibuat dari Job {job.number}."
        )
        return redirect("billing:invoice_detail", pk=invoice.pk)


class GenerateDPInvoiceView(LoginRequiredMixin, View):
    def post(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)

        try:
            invoice = generate_invoice_from_job(
                job,
                Invoice.INV_DP,
                request.user
            )

            messages.success(request, "DP invoice created successfully.")
            return redirect("billing:invoice_detail", pk=invoice.pk)

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect("job:job_order_detail", pk=job.pk)
        


class GenerateFinalInvoiceView(LoginRequiredMixin, View):
    def post(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)

        try:
            invoice = generate_invoice_from_job(
                job,
                Invoice.INV_FINAL,
                request.user
            )

            messages.success(request, "Final invoice created successfully.")
            return redirect("billing:invoice_detail", pk=invoice.pk)

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect("job:job_order_detail", pk=job.pk)      



