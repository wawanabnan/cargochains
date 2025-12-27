from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView

from accounting.models.period_lock import AccountingPeriodLock


class PeriodLockListView(LoginRequiredMixin, ListView):
    model = AccountingPeriodLock
    template_name = "period_locks/list.html"
    context_object_name = "rows"
    paginate_by = 50


class PeriodLockCreateView(LoginRequiredMixin, CreateView):
    model = AccountingPeriodLock
    fields = ["year", "month", "is_locked"]
    template_name = "period_locks/form.html"

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "Period sudah ada (year+month).")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("accounting:period_lock_list")


class PeriodLockUpdateView(LoginRequiredMixin, UpdateView):
    model = AccountingPeriodLock
    fields = ["year", "month", "is_locked"]
    template_name = "period_locks/form.html"

    def get_success_url(self):
        return reverse("accounting:period_lock_list")


class PeriodLockToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(AccountingPeriodLock, pk=pk)
        obj.is_locked = not obj.is_locked
        obj.save(update_fields=["is_locked"])
        messages.success(request, f"Period {obj.year}-{obj.month:02d} -> {'LOCKED' if obj.is_locked else 'OPEN'}")
        return redirect("accounting:period_lock_list")
