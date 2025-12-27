from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views import View

from accounting.forms.journals import JournalForm, JournalLineFormSet
from accounting.models.journal import Journal
from accounting.services.numbering import next_journal_number


def _sum_lines(formset):
    td = Decimal("0.00")
    tc = Decimal("0.00")

    for f in formset.forms:
        if not f.cleaned_data:
            continue
        if f.cleaned_data.get("DELETE"):
            continue

        debit = f.cleaned_data.get("debit") or Decimal("0.00")
        credit = f.cleaned_data.get("credit") or Decimal("0.00")
        account = f.cleaned_data.get("account")

        # skip empty rows (no account + no amount)
        if (account is None) and (debit == 0) and (credit == 0):
            continue

        td += debit
        tc += credit

    return td, tc


class JournalCreateView(LoginRequiredMixin, View):
    template_name = "journals/form.html"

    def get(self, request):
        form = JournalForm()
        formset = JournalLineFormSet()
        return render(request, self.template_name, {"form": form, "formset": formset, "mode": "create"})

    @transaction.atomic
    def post(self, request):
        form = JournalForm(request.POST)
        formset = JournalLineFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            td, tc = _sum_lines(formset)
            if td != tc:
                messages.error(request, f"Journal belum balance. Debit={td} Credit={tc}")
                return render(request, self.template_name, {"form": form, "formset": formset, "mode": "create"})

            j = form.save(commit=False)
            j.number = next_journal_number(j.date)
            j.posted = False
            j.save()

            formset.instance = j
            formset.save()

            messages.success(request, f"Journal {j.number} berhasil dibuat.")
            return redirect(reverse("accounting:journal_detail", args=[j.pk]))

        return render(request, self.template_name, {"form": form, "formset": formset, "mode": "create"})


class JournalUpdateView(LoginRequiredMixin, View):
    template_name = "journals/form.html"

    def get(self, request, pk):
        j = get_object_or_404(Journal, pk=pk)
        if j.posted:
            messages.error(request, "Journal sudah POSTED, tidak bisa diedit.")
            return redirect(reverse("accounting:journal_detail", args=[j.pk]))

        form = JournalForm(instance=j)
        formset = JournalLineFormSet(instance=j)
        return render(request, self.template_name, {"form": form, "formset": formset, "journal": j, "mode": "edit"})

    @transaction.atomic
    def post(self, request, pk):
        j = get_object_or_404(Journal, pk=pk)
        if j.posted:
            messages.error(request, "Journal sudah POSTED, tidak bisa diedit.")
            return redirect(reverse("accounting:journal_detail", args=[j.pk]))

        form = JournalForm(request.POST, instance=j)
        formset = JournalLineFormSet(request.POST, instance=j)

        if form.is_valid() and formset.is_valid():
            td, tc = _sum_lines(formset)
            if td != tc:
                messages.error(request, f"Journal belum balance. Debit={td} Credit={tc}")
                return render(request, self.template_name, {"form": form, "formset": formset, "journal": j, "mode": "edit"})

            form.save()
            formset.save()

            messages.success(request, f"Journal {j.number} berhasil diupdate.")
            return redirect(reverse("accounting:journal_detail", args=[j.pk]))

        return render(request, self.template_name, {"form": form, "formset": formset, "journal": j, "mode": "edit"})
