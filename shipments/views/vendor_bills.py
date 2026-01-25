from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from shipments.forms.vendor_bills  import VendorBillForm, VendorBillLineFormSet

from shipments.models.vendor_bills import VendorBill

TEMPLATE_LIST = "vendor_bills/list.html"
TEMPLATE_FORM = "vendor_bills/form.html"


class VendorBillListView(LoginRequiredMixin, View):
    def get(self, request):
        qs = VendorBill.objects.select_related("vendor", "currency").order_by("-id")
        return render(request, TEMPLATE_LIST, {"items": qs})


class VendorBillCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = VendorBillForm()
        formset = VendorBillLineFormSet()
        return render(request, TEMPLATE_FORM, {"form": form, "formset": formset, "mode": "add"})

    @transaction.atomic
    def post(self, request):
        form = VendorBillForm(request.POST)
        formset = VendorBillLineFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.status = "POSTED"  # atau DRAFT dulu kalau kamu mau approval
            obj.save()

            formset.instance = obj
            formset.save()

            obj.recalc_total()
            obj.save(update_fields=["total_amount"])

            messages.success(request, "Vendor Bill tersimpan ✅")
            return redirect("payments:vendor_bill_edit", pk=obj.pk)

        messages.error(request, "Ada error. Cek field merah.")
        return render(request, TEMPLATE_FORM, {"form": form, "formset": formset, "mode": "add"})


class VendorBillUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(VendorBill, pk=pk)
        form = VendorBillForm(instance=obj)
        formset = VendorBillLineFormSet(instance=obj)
        return render(request, TEMPLATE_FORM, {"obj": obj, "form": form, "formset": formset, "mode": "edit"})

    @transaction.atomic
    def post(self, request, pk):
        obj = get_object_or_404(VendorBill, pk=pk)
        form = VendorBillForm(request.POST, instance=obj)
        formset = VendorBillLineFormSet(request.POST, instance=obj)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()

            obj.recalc_total()
            obj.save(update_fields=["total_amount"])

            messages.success(request, "Vendor Bill tersimpan ✅")
            return redirect("payments:vendor_bill_edit", pk=obj.pk)

        messages.error(request, "Ada error. Cek field merah.")
        return render(request, TEMPLATE_FORM, {"obj": obj, "form": form, "formset": formset, "mode": "edit"})
