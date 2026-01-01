from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from sales.job_order_model import JobOrder,JobCost, JobOrderAttachment
from sales.forms.job_order import JobOrderForm
from sales.forms.job_cost import JobCostFormSet
from sales.forms.job_attachment import JobOrderAttachmentForm

from django.views.generic import ListView

from partners.models import Customer
from core.models.services import Service
from core.models.currencies import Currency
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from core.utils import get_next_number
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseBadRequest
from decimal import Decimal, InvalidOperation


from sales.models import JobOrder, Invoice, InvoiceLine
from sales.utils.invoices import generate_invoice_from_job


# ==========================
# LIST
# ==========================

class JobOrderListView(LoginRequiredMixin, ListView):
    model = JobOrder
    template_name = "job_orders/list.html"
    context_object_name = "job_orders"
    paginate_by = 19

    def get_queryset(self):
        qs = (
            JobOrder.objects
            .select_related("customer", "service", "payment_term", "currency", "sales_user")
            .order_by("-job_date", "-id")
        )

        sort = self.request.GET.get("sort", "-job_date")  # default
        allowed = {
            "number", "-number",
            "job_date", "-job_date",
            "customer__name", "-customer__name",
            "grand_total", "-grand_total",
        }

        if sort in allowed:
            qs = qs.order_by(sort)


        q = self.request.GET.get("q")
        customer_id = self.request.GET.get("customer")
        service_id = self.request.GET.get("service")
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        if q:
            qs = qs.filter(number__icontains=q) | qs.filter(cargo_description__icontains=q)

        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        if service_id:
            qs = qs.filter(service_id=service_id)

        if date_from:
            qs = qs.filter(job_date__gte=date_from)

        if date_to:
            qs = qs.filter(job_date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # nilai filter agar dropdown tetap selected
        ctx["filter_q"] = self.request.GET.get("q", "")
        ctx["filter_customer"] = self.request.GET.get("customer", "")
        ctx["filter_service"] = self.request.GET.get("service", "")
        ctx["filter_date_from"] = self.request.GET.get("date_from", "")
        ctx["filter_date_to"] = self.request.GET.get("date_to", "")

        # dropdown data
        ctx["customers"] = Customer.objects.all().order_by("name")
        ctx["services"] = Service.objects.all().order_by("name")

        return ctx

# ==========================
# CREATE
# ==========================
class JobOrderCreateView2(LoginRequiredMixin, View):
    template_name = "job_orders/h_form.html"

    def get(self, request):
        form = JobOrderForm()
        return render(request, self.template_name, {
            "form": form,
            "job": None,
            "cost_formset": None,  # tidak tampil saat new
        })

    def post(self, request):
        form = JobOrderForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Form tidak valid, silakan diperiksa kembali.")
            return render(request, self.template_name, {
                "form": form,
                "job": None,
                "cost_formset": None,
            })

        job = form.save(commit=False)
        job.sales_user = request.user
        job.status = JobOrder.ST_IN_PROGRESS  # atau ST_IN_PROGRESS sesuai konstanta om

        job.save()

        messages.success(request, "Job Order berhasil dibuat.")

        # redirect ke edit untuk input JobCost
        return redirect("sales:job_order_edit", pk=job.pk)


class JobOrderCreateView(LoginRequiredMixin, View):
    template_name = "job_orders/h_form.html"

    def get(self, request):
        form = JobOrderForm()
        return render(request, self.template_name, {
            "form": form,
            "job": None,
            "cost_formset": None,
        })

    def post(self, request):
        # =====================================================
        # 🔧 NORMALISASI POST DATA (FIX "Enter a number.")
        # =====================================================
        data = request.POST.copy()

        currency_id = data.get("currency")
        if currency_id:
            cur = Currency.objects.filter(pk=currency_id).only("code").first()
            code = (cur.code or "").upper() if cur else ""

            if code == "IDR":
                # ✅ IDR → kurs FIX = 1 (angka valid)
                data["kurs_idr"] = "1"
            else:
                # 🌍 Non-IDR → normalisasi format indo ke decimal
                raw = (data.get("kurs_idr") or "").strip()
                if raw:
                    raw = raw.replace(" ", "").replace(".", "").replace(",", ".")
                    data["kurs_idr"] = raw

        # =====================================================
        # FORM VALIDATION
        # =====================================================
        form = JobOrderForm(data)

        if not form.is_valid():
            messages.error(request, "Form tidak valid, silakan diperiksa kembali.")
            return render(request, self.template_name, {
                "form": form,
                "job": None,
                "cost_formset": None,
            })

        # =====================================================
        # SAVE JOB ORDER
        # =====================================================
        job = form.save(commit=False)
        job.sales_user = request.user
        job.status = JobOrder.ST_IN_PROGRESS


        # safety net (double lock)
        if job.currency and (job.currency.code or "").upper() == "IDR":
            job.kurs_idr = Decimal("1.00")

        job.save()

        messages.success(request, "Job Order berhasil dibuat.")
        return redirect("sales:job_order_edit", pk=job.pk)


# ==========================
# UPDATE
# ==========================

class JobOrderUpdateView(LoginRequiredMixin, View):
    template_name = "job_orders/edit_form.html"

    def get_object(self, pk):
        return get_object_or_404(JobOrder, pk=pk)

    def get(self, request, pk):
        job = self.get_object(pk)
        form = JobOrderForm(instance=job)
        cost_formset = JobCostFormSet(instance=job)

        ctx = {
            "form": form,
            "job": job,
            "cost_formset": cost_formset,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        job = self.get_object(pk)

        form = JobOrderForm(request.POST, instance=job)
        cost_formset = JobCostFormSet(request.POST, instance=job)

        

        if form.is_valid() and cost_formset.is_valid():
            job = form.save(commit=False)
            if not job.sales_user_id:
                job.sales_user = request.user
            job.save()

            # pastikan formset nempel ke job yang barusan disave
            cost_formset.instance = job
            cost_formset.save()

            messages.success(request, "Job Order & Job Cost berhasil diupdate.")
            return redirect("sales:job_order_detail", pk=job.pk)

        # kalau ada masalah, TAMPILKAN error, jangan diam-diam
        messages.error(request, "Form Job Order atau Job Cost belum benar, silakan dicek lagi.")
        ctx = {
            "form": form,
            "job": job,
            "cost_formset": cost_formset,
        }
        return render(request, self.template_name, ctx)

        
# ==========================
# DETAIL
# ==========================

class JobOrderDetailView(LoginRequiredMixin, DetailView):
    model = JobOrder
    template_name = "job_orders/detail.html"
    context_object_name = "job"

    def get_context_data2(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = self.object

        # Ambil job cost EXPLISIT lewat FK, bukan related_name
        costs = JobCost.objects.filter(job_order=job).order_by("id")
        total_cost = costs.aggregate(total=Sum("amount"))["total"] or 0

        ctx["costs"] = costs
        ctx["total_cost"] = total_cost
        ctx["attachments"] = job.attachments.all()
        ctx["attachment_form"] = JobOrderAttachmentForm()
        return ctx
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = self.object

 

        costs = JobCost.objects.filter(job_order=job).order_by("id")
        total_cost = costs.aggregate(total=Sum("amount"))["total"] or 0

        ctx["costs"] = costs
        ctx["total_cost"] = total_cost

        # ✅ ini yang baru: formset untuk edit di detail
        ctx["cost_formset"] = JobCostFormSet(instance=job)

        ctx["attachments"] = job.attachments.all()
        ctx["attachment_form"] = JobOrderAttachmentForm()
        ctx["cost_formset"] = JobCostFormSet(instance=job)  # ✅ INI WAJIB

        return ctx
    

class JobOrderAttachmentUploadView(LoginRequiredMixin, View):
    """
    Terima POST (multipart) untuk upload attachment job order.
    """

    def post(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)
        form = JobOrderAttachmentForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Upload gagal. Pastikan file dipilih dan format benar.")
            return redirect("sales:job_order_detail", pk=job.pk)

        att = form.save(commit=False)
        att.job_order = job
        att.uploaded_by = request.user
        att.save()

        messages.success(request, "Attachment berhasil ditambahkan.")
        return redirect("sales:job_order_detail", pk=job.pk)


class JobOrderAttachmentDeleteView(LoginRequiredMixin, View):
    """
    Hapus satu attachment job order.
    """

    def post(self, request, pk, att_id):
        job = get_object_or_404(JobOrder, pk=pk)
        att = get_object_or_404(JobOrderAttachment, pk=att_id, job_order=job)

        # (Opsional) bisa cek permission dulu di sini

        att.file.delete(save=False)  # hapus file fisik
        att.delete()
        messages.success(request, "Attachment berhasil dihapus.")
        return redirect("sales:job_order_detail", pk=job.pk)


class JobOrderBulkStatusView(LoginRequiredMixin, View):
    def post(self, request):
        action = request.POST.get("action")
        ids = request.POST.getlist("ids[]")

        if not ids:
            messages.info(request, "Tidak ada Job Order yang dipilih.")
            return redirect("sales:job_order_list")

        qs = JobOrder.objects.filter(pk__in=ids).exclude(status=JobOrder.ST_COMPLETED)

        if action == "pending":
            updated = qs.filter(status=JobOrder.ST_IN_PROGRESS).update(status=JobOrder.ST_PENDING)
            messages.success(request, f"{updated} Job Order berhasil di-set Pending.")

        elif action == "cancel":
            updated = qs.exclude(status=JobOrder.ST_CANCELLED).update(status=JobOrder.ST_CANCELLED)
            messages.warning(request, f"{updated} Job Order berhasil di-cancel.")

        else:
            messages.error(request, "Action tidak valid.")

        return redirect("sales:job_order_list")


from django.db import transaction

class JobOrderCostsUpdateView(LoginRequiredMixin, View):
    template_name = "job_orders/detail.html"

    @transaction.atomic
    def post(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)

        cost_formset = JobCostFormSet(request.POST, instance=job)
        prefix = cost_formset.prefix
        print("====== JOB COST DEBUG ======")
        print("PREFIX:", prefix)
        print("TOTAL_FORMS:", request.POST.get(f"{prefix}-TOTAL_FORMS"))
        print("INITIAL_FORMS:", request.POST.get(f"{prefix}-INITIAL_FORMS"))
        print("ID(0):", request.POST.get(f"{prefix}-0-id"))
        print("POST id keys:", [k for k in request.POST.keys() if k.endswith("-id")])
        print("================================")
        # ===== DEBUG END =====        
        
        if cost_formset.is_valid():
            cost_formset.save()
            messages.success(request, "Job Cost berhasil diupdate.")
            return redirect("sales:job_order_detail", pk=job.pk)

        # kalau invalid → render halaman detail yang sama (tab cost), tampilkan error
        messages.error(request, "Ada error pada Job Cost. Silakan dicek.")
        # tetap tampilkan costs & total untuk panel summary (optional)
        costs = JobCost.objects.filter(job_order=job).order_by("id")
        total_cost = costs.aggregate(total=Sum("amount"))["total"] or 0

        return render(request, self.template_name, {
            "job": job,
            "cost_formset": cost_formset,
            "costs": costs,
            "total_cost": total_cost,
            "attachments": job.attachments.all(),
            "attachment_form": JobOrderAttachmentForm(),
        })


class JobOrderGenerateInvoiceView(LoginRequiredMixin, View):
    def post(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)

        invoice = generate_invoice_from_job(job)

        messages.success(
            request,
            f"Invoice {invoice.number} berhasil dibuat dari Job {job.number}."
        )
        return redirect("sales:invoice_detail", pk=invoice.pk)