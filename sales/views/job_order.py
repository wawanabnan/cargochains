from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from sales.job_order_model import JobOrder
from sales.forms_job_order import JobOrderForm
from django.views.generic import ListView

from partners.models import Partner
from core.models import Service  #
from django.views.generic import ListView, CreateView, UpdateView, DetailView

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
        ctx["filter_q"] = self.request.GET.get("q", "")
        ctx["filter_customer"] = self.request.GET.get("customer", "")
        ctx["filter_service"] = self.request.GET.get("service", "")
        ctx["filter_date_from"] = self.request.GET.get("date_from", "")
        ctx["filter_date_to"] = self.request.GET.get("date_to", "")

        # Dropdown customer (role customer) & service
        try:
            customers = (
                Partner.objects
                .filter(roles__role_type__code="customer")
                .order_by("name")
            )
        except Exception:
            customers = Partner.objects.all().order_by("name")

        services = Service.objects.all().order_by("name")

        ctx["customers"] = customers
        ctx["services"] = services
        return ctx


class JobOrderCreateView(LoginRequiredMixin, CreateView):
    model = JobOrder
    form_class = JobOrderForm
    template_name = "job_orders/h_form.html"

    def form_valid(self, form):
        obj = form.save(commit=False)

        # set sales_user default ke user login saat create
        if not obj.sales_user_id:
            obj.sales_user = self.request.user

        obj.sales_user = self.request.user   # otomatis
        obj.save()
        messages.success(self.request, "Job Order berhasil dibuat.")

        # habis create mau balik ke list atau langsung ke edit? pilih salah satu
        return redirect("sales:job_edit", pk=obj.pk)
        # atau:
        # return redirect("sales:job_list")


# ==============
# UPDATE VIEW
# ==============
class JobOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = JobOrder
    form_class = JobOrderForm
    template_name = "job_orders/h_form.html"
    context_object_name = "job"

    def form_valid(self, form):
        obj = form.save(commit=False)
        # sales_user tidak diubah kalau sudah ada, kecuali mau dipaksa
        if not obj.sales_user_id:       # kalau sebelumnya kosong
            obj.sales_user = self.request.user

        obj.save()
        messages.success(self.request, "Job Order berhasil diupdate.")
        return redirect("sales:job_edit", pk=obj.pk)
        # atau:
        # return redirect("sales:job_list")

class JobOrderDetailView(LoginRequiredMixin, DetailView):
    model = JobOrder
    template_name = "job_orders/detail.html"
    context_object_name = "job"