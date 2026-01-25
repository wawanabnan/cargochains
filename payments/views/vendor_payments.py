# payments/views/vendor_payment.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from payments.forms.vendor_payments import VendorPaymentForm, VendorPaymentLineFormSet
from payments.models.vendor_payments import VendorPayment


class VendorPaymentListView(LoginRequiredMixin, View):
    def get(self, request):
        qs = VendorPayment.objects.select_related("vendor", "currency").all()
        return render(request, "vendor_payments/list.html", {"items": qs})


class VendorPaymentCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = VendorPaymentForm()
        formset = VendorPaymentLineFormSet()
        return render(request, "vendor_payments/form.html", {"form": form, "formset": formset, "mode": "add"})

    @transaction.atomic
    def post(self, request):
        form = VendorPaymentForm(request.POST)
        formset = VendorPaymentLineFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.status = "DRAFT"
            obj.save()

            formset.instance = obj
            formset.save()

            obj.recalc_total()
            obj.save(update_fields=["total_amount"])

            messages.success(request, "Vendor Payment tersimpan ✅")
            return redirect("payments:vendor_payment_edit", pk=obj.pk)

        messages.error(request, "Ada error. Cek field merah.")
        return render(request, "vendor_payment/form.html", {"form": form, "formset": formset, "mode": "add"})


class VendorPaymentUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(VendorPayment, pk=pk)
        form = VendorPaymentForm(instance=obj)
        formset = VendorPaymentLineFormSet(instance=obj)
        return render(
            request,
            "vendor_payment/form.html",
            {"obj": obj, "form": form, "formset": formset, "mode": "edit"},
        )

    @transaction.atomic
    def post(self, request, pk):
        obj = get_object_or_404(VendorPayment, pk=pk)

        if obj.status != "DRAFT":
            messages.error(request, "Payment sudah Posted/Voided, tidak bisa diedit.")
            return redirect("payments:vendor_payment_edit", pk=obj.pk)

        form = VendorPaymentForm(request.POST, instance=obj)
        formset = VendorPaymentLineFormSet(request.POST, instance=obj)

        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.save()

            obj.recalc_total()
            obj.save(update_fields=["total_amount"])

            messages.success(request, "Tersimpan ✅")
            return redirect("payments:vendor_payment_edit", pk=obj.pk)

        messages.error(request, "Ada error. Cek field merah.")
        return render(
            request,
            "vendor_payment/form.html",
            {"obj": obj, "form": form, "formset": formset, "mode": "edit"},
        )
