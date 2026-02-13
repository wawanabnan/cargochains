from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import ListView, DetailView, UpdateView

from shipments.models.shipping_instruction import ShippingInstructionDocument, SeaShippingInstructionDetail
from shipments.forms.shipping_instruction import (
    ShippingInstructionDocumentForm,
    SeaShippingInstructionDetailForm,
)
from work_orders.models.vendor_bookings import VendorBooking


class ShippingInstructionListView(LoginRequiredMixin, ListView):
    model = ShippingInstructionDocument
    template_name = "shipping_instructions/list.html"
    context_object_name = "items"
    paginate_by = 30

    def get_queryset(self):
        qs = (
            ShippingInstructionDocument.objects
            .select_related("vendor_booking", "job_order", "issued_by")
            .order_by("-id")
        )

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(document_no__icontains=q)

        status = (self.request.GET.get("status") or "").strip().upper()
        if status in ("DRAFT", "ISSUED", "CANCELLED"):
            qs = qs.filter(status=status)

        return qs


class ShippingInstructionDetailView(LoginRequiredMixin, DetailView):
    model = ShippingInstructionDocument
    template_name = "shipping_instructions/detail.html"
    context_object_name = "doc"


class ShippingInstructionUpdateView(LoginRequiredMixin, UpdateView):
    model = ShippingInstructionDocument
    form_class = ShippingInstructionDocumentForm
    template_name = "shipping_instructions/form.html"
    context_object_name = "doc"

    def get_success_url(self):
        return reverse("shipments:si_update", args=[self.object.pk])

    def _ensure_sea_detail(self, doc):
        detail = getattr(doc, "sea_detail", None)
        if detail is None:
            detail = SeaShippingInstructionDetail.objects.create(document=doc)
        return detail

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        detail = self._ensure_sea_detail(self.object)
        ctx.setdefault("sea_form", SeaShippingInstructionDetailForm(instance=detail))
        return ctx

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # lock kalau cancelled
        if self.object.status == ShippingInstructionDocument.Status.CANCELLED:
            messages.warning(request, "Shipping Instruction sudah CANCELLED. Tidak bisa diedit.")
            return redirect(self.get_success_url())

        form = self.get_form()
        detail = self._ensure_sea_detail(self.object)
        sea_form = SeaShippingInstructionDetailForm(request.POST, instance=detail)

        if form.is_valid() and sea_form.is_valid():
            form.save()
            sea_form.save()
            messages.success(request, "Shipping Instruction tersimpan ✅")
            return redirect(self.get_success_url())

        ctx = self.get_context_data(form=form)
        ctx["sea_form"] = sea_form
        return render(request, self.template_name, ctx)

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Lock kalau SI cancelled
        if self.object.status == ShippingInstructionDocument.Status.CANCELLED:
            messages.warning(request, "Shipping Instruction sudah CANCELLED. Tidak bisa diedit.")
            return redirect("shipments:si_detail", pk=self.object.pk)

        # Optional extra lock: kalau SO cancelled/done
        vb = self.object.vendor_booking
        if vb and vb.status in (VendorBooking.ST_CANCELLED, VendorBooking.ST_DONE):
            messages.warning(request, "Service Order sudah dikunci. Shipping Instruction tidak bisa diedit.")
            return redirect("shipments:si_detail", pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)
    

from django.http import HttpResponseBadRequest
from django.utils import timezone
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from shipments.models.shipping_instruction import ShippingInstructionDocument


class ShippingInstructionIssueView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        doc = get_object_or_404(ShippingInstructionDocument, pk=pk)

        # sudah cancelled → tidak boleh issue
        if doc.status == ShippingInstructionDocument.Status.CANCELLED:
            messages.error(request, "Document already CANCELLED.")
            return redirect("shipments:si_update", pk=doc.pk)

        # kalau sudah issued → skip
        if doc.status == ShippingInstructionDocument.Status.ISSUED:
            messages.info(request, "Document already ISSUED.")
            return redirect("shipments:si_update", pk=doc.pk)

        # set ISSUED
        doc.status = ShippingInstructionDocument.Status.ISSUED
        doc.save(update_fields=["status"])

        messages.success(request, "Shipping Instruction ISSUED ✅")
        return redirect("shipments:si_update", pk=doc.pk)


class ShippingInstructionCancelView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        doc = get_object_or_404(ShippingInstructionDocument, pk=pk)

        if doc.status == ShippingInstructionDocument.Status.CANCELLED:
            messages.warning(request, "Already cancelled.")
            return redirect("shipments:si_update", pk=doc.pk)

        doc.status = ShippingInstructionDocument.Status.CANCELLED
        doc.cancelled_at = timezone.now()
        doc.cancelled_by = request.user
        doc.save(update_fields=["status", "cancelled_at", "cancelled_by"])

        messages.warning(request, "Shipping Instruction cancelled ⚠️")
        return redirect("shipments:si_update", pk=doc.pk)
