# core/views/services.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView

from core.models.services import Service
from core.forms.services import ServiceForm


class ServiceListView(LoginRequiredMixin, ListView):
    model = Service
    template_name = "services/list.html"
    context_object_name = "services"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(code__icontains=q)
                | Q(name__icontains=q)
                | Q(service_group__icontains=q)
            )
        return qs


class ServiceCreateView(LoginRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = "services/form.html"
    success_url = reverse_lazy("core:service_list")


class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = "services/form.html"
    success_url = reverse_lazy("core:service_list")


class ServiceDetailView(LoginRequiredMixin, DetailView):
    model = Service
    template_name = "services/detail.html"
    context_object_name = "service"


class ServiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Service
    template_name = "services/confirm_delete.html"
    success_url = reverse_lazy("core:service_list")
    context_object_name = "service"
