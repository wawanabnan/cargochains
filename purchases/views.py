
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from . import models as m
from .forms import PurchaseOrderForm, PurchaseOrderLineFormSet

class PurchaseOrderListView(View):
    template_name = "purchases/po_list.html"

    def get(self, request):
        qs = (
            m.PurchaseOrder.objects
            .select_related("vendor__partner", "vendor__role_type", "currency", "purchase_user")

        )
        q = request.GET.get("q") or ""
        status = request.GET.get("status") or ""
        dfrom = request.GET.get("date_from") or ""
        dto = request.GET.get("date_to") or ""

        if q:
            qs = qs.filter(
                Q(number__icontains=q) | Q(ref_number__icontains=q) |
                Q(supplier__partner__name__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if dfrom:
            qs = qs.filter(order_date__gte=dfrom)
        if dto:
            qs = qs.filter(order_date__lte=dto)

        qs = qs.order_by("-order_date", "-created_at")

        from django.core.paginator import Paginator
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))

        context = {
            "page_obj": page_obj,
            "statuses": m.PurchaseOrder.STATUS_CHOICES,
            "status_selected": status, "q": q,
            "date_from": dfrom, "date_to": dto,
        }
        return render(request, self.template_name, context)

class PurchaseOrderCreateView(View):
    template_name = "purchases/po_form.html"

    def get(self, request):
        form = PurchaseOrderForm()
        formset = PurchaseOrderLineFormSet()
        return render(request, self.template_name, {"form": form, "formset": formset, "po": None})

    @transaction.atomic
    def post(self, request):
        form = PurchaseOrderForm(request.POST, request.FILES)
        formset = PurchaseOrderLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            po = form.save(commit=False)
            po.ensure_number()
            po.save()
            formset.instance = po
            formset.save()
            po.recompute_totals()
            po.save(update_fields=["subtotal_amount", "discount_amount", "tax_percent", "tax_amount", "total_amount"])
            messages.success(request, f"PO '{po.number}' berhasil dibuat.")
            return redirect(reverse("purchases:po_edit", args=[po.pk]))
        return render(request, self.template_name, {"form": form, "formset": formset, "po": None})

class PurchaseOrderUpdateView(View):
    template_name = "purchases/po_form.html"

    def get(self, request, pk):
        po = get_object_or_404(m.PurchaseOrder, pk=pk)
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderLineFormSet(instance=po)
        return render(request, self.template_name, {"form": form, "formset": formset, "po": po})

    @transaction.atomic
    def post(self, request, pk):
        po = get_object_or_404(m.PurchaseOrder, pk=pk)
        form = PurchaseOrderForm(request.POST, request.FILES, instance=po)
        formset = PurchaseOrderLineFormSet(request.POST, instance=po)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            po.recompute_totals()
            po.save(update_fields=["subtotal_amount", "discount_amount", "tax_percent", "tax_amount", "total_amount"])
            messages.success(request, f"PO '{po.number}' diperbarui.")
            return redirect(reverse("purchases:po_edit", args=[po.pk]))
        return render(request, self.template_name, {"form": form, "formset": formset, "po": po})
