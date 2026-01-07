from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.models.uoms import UOM
from core.forms.uoms import UOMForm


class UOMListView(LoginRequiredMixin, ListView):
    model = UOM
    template_name = "uoms/list.html"
    context_object_name = "rows"
    paginate_by = 25

    def get_queryset(self):
        qs = UOM.objects.all().order_by("code")

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(code__icontains=q) |
                Q(name__icontains=q) |
                Q(category__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        return ctx


class UOMCreateView(LoginRequiredMixin, CreateView):
    model = UOM
    form_class = UOMForm
    template_name = "uoms/form.html"
    success_url = reverse_lazy("core:uom_list")

    def form_valid(self, form):
        messages.success(self.request, "Unit of Measurement berhasil ditambahkan.")
        return super().form_valid(form)


class UOMUpdateView(LoginRequiredMixin, UpdateView):
    model = UOM
    form_class = UOMForm
    template_name = "uoms/form.html"
    success_url = reverse_lazy("core:uom_list")

    def form_valid(self, form):
        messages.success(self.request, "Unit of Measurement berhasil diupdate.")
        return super().form_valid(form)


class UOMDeleteView(LoginRequiredMixin, DeleteView):
    model = UOM
    template_name = "core/settings/uom_confirm_delete.html"
    success_url = reverse_lazy("core:uom_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Unit of Measurement berhasil dihapus.")
        return super().delete(request, *args, **kwargs)
