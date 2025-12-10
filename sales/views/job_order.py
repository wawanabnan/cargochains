from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from sales.job_order_model import JobOrder,JobCost
from sales.forms_job_order import JobOrderForm
from sales.forms_job_cost import JobCostFormSet
from django.views.generic import ListView

from partners.models import Partner
from core.models import Service  #
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from core.utils import get_next_number
from django.db.models import Sum


# ==========================
# LIST
# ==========================
class JobOrderListView(LoginRequiredMixin, ListView):
    model = JobOrder
    template_name = "job_orders/list.html"
    context_object_name = "job_orders"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            JobOrder.objects
            .select_related("customer", "service", "payment_term", "sales_user")
            .order_by("-job_date", "-id")
        )

        # filter sederhana (opsional, boleh kamu kembangkan lagi)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(number__icontains=q) | qs.filter(cargo_description__icontains=q)

        return qs


# ==========================
# CREATE
# ==========================
class JobOrderCreateView(LoginRequiredMixin, View):
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
        job.save()

        messages.success(request, "Job Order berhasil dibuat.")

        # redirect ke edit untuk input JobCost
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = self.object

        # Ambil job cost EXPLISIT lewat FK, bukan related_name
        costs = JobCost.objects.filter(job_order=job).order_by("id")
        total_cost = costs.aggregate(total=Sum("amount"))["total"] or 0

        ctx["costs"] = costs
        ctx["total_cost"] = total_cost
        return ctx