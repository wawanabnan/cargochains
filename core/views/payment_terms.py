# core/views/payment_terms.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.forms.payment_terms import PaymentTermForm
from core.models.payment_terms import PaymentTerm


class PaymentTermListView(LoginRequiredMixin, ListView):
    model = PaymentTerm
    template_name = "payment_terms/list.html"
    context_object_name = "items"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        return ctx


class PaymentTermCreateView(LoginRequiredMixin, CreateView):
    model = PaymentTerm
    form_class = PaymentTermForm
    template_name = "payment_terms/form.html"
    success_url = reverse_lazy("core_settings:payment_term_list")

    def form_valid(self, form):
        messages.success(self.request, "Payment Term berhasil dibuat.")
        return super().form_valid(form)


class PaymentTermUpdateView(LoginRequiredMixin, UpdateView):
    model = PaymentTerm
    form_class = PaymentTermForm
    template_name = "payment_terms/form.html"
    success_url = reverse_lazy("core:payment_term_list")

    def form_valid(self, form):
        messages.success(self.request, "Payment Term berhasil diupdate.")
        return super().form_valid(form)


class PaymentTermDeleteView(LoginRequiredMixin, DeleteView):
    model = PaymentTerm
    template_name = "payment_terms/confirm_delete.html"
    success_url = reverse_lazy("core:payment_term_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Payment Term berhasil dihapus.")
        return super().delete(request, *args, **kwargs)


class PaymentTermSetDefaultView(LoginRequiredMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(PaymentTerm, pk=pk)

        with transaction.atomic():
            PaymentTerm.objects.filter(is_default=True).update(is_default=False)
            obj.is_default = True
            obj.save(update_fields=["is_default", "updated_at"])

        messages.success(request, f"Default Payment Term diset ke: {obj.code} - {obj.name}")
        return redirect("core:payment_term_list")
