from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.models.exchange_rates import ExchangeRate
from core.forms.exchange_rates import ExchangeRateForm


class ExchangeRateListView(LoginRequiredMixin, ListView):
    model = ExchangeRate
    template_name = "exchange_rates/list.html"
    context_object_name = "rows"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            ExchangeRate.objects
            .select_related("currency")
            .order_by("-rate_date", "currency__code")
        )

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(currency__code__icontains=q) |
                Q(currency__name__icontains=q) |
                Q(source__icontains=q)
            )

        d = (self.request.GET.get("date") or "").strip()
        if d:
            qs = qs.filter(rate_date=d)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["date"] = (self.request.GET.get("date") or "").strip()
        return ctx


class ExchangeRateCreateView(LoginRequiredMixin, CreateView):
    model = ExchangeRate
    form_class = ExchangeRateForm
    template_name = "exchange_rate_form.html"
    success_url = reverse_lazy("core:exchange_rate_list")

    def form_valid(self, form):
        messages.success(self.request, "Exchange rate berhasil ditambahkan.")
        return super().form_valid(form)


class ExchangeRateUpdateView(LoginRequiredMixin, UpdateView):
    model = ExchangeRate
    form_class = ExchangeRateForm
    template_name = "exchange_rates/form.html"
    success_url = reverse_lazy("core:exchange_rate_list")

    def form_valid(self, form):
        messages.success(self.request, "Exchange rate berhasil diupdate.")
        return super().form_valid(form)


class ExchangeRateDeleteView(LoginRequiredMixin, DeleteView):
    model = ExchangeRate
    template_name = "exchange_rates/confirm_delete.html"
    success_url = reverse_lazy("core:settings_exchange_rate_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Exchange rate berhasil dihapus.")
        return super().delete(request, *args, **kwargs)
