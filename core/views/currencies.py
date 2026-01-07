# core/views/currencies.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.models.currencies import Currency
from core.forms.currencies import CurrencyForm


class CurrencyListView(LoginRequiredMixin, ListView):
    model = Currency
    template_name = "currencies/list.html"
    context_object_name = "rows"
    paginate_by = 25

    def get_queryset(self):
        qs = Currency.objects.all().order_by("code")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        return ctx


class CurrencyCreateView(LoginRequiredMixin, CreateView):
    model = Currency
    form_class = CurrencyForm
    template_name = "currencies/form.html"
    success_url = reverse_lazy("core:currency_list")

    def form_valid(self, form):
        messages.success(self.request, "Currency berhasil ditambahkan.")
        return super().form_valid(form)


class CurrencyUpdateView(LoginRequiredMixin, UpdateView):
    model = Currency
    form_class = CurrencyForm
    template_name = "currencies/form.html"
    success_url = reverse_lazy("core:currency_list")

    def form_valid(self, form):
        messages.success(self.request, "Currency berhasil diupdate.")
        return super().form_valid(form)


class CurrencyDeleteView(LoginRequiredMixin, DeleteView):
    model = Currency
    template_name = "currencies/confirm_delete.html"
    success_url = reverse_lazy("core:currency_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Currency berhasil dihapus.")
        return super().delete(request, *args, **kwargs)
