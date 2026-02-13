# work_orders/views/service_orders/actions.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from work_orders.models.vendor_bookings import VendorBooking
from shipments.models.shipping_instruction import (
    ShippingInstructionDocument,
    SeaShippingInstructionDetail,
)

ALLOWED_TRANSITIONS = {
    VendorBooking.ST_DRAFT: {VendorBooking.ST_SUBMITTED},
    VendorBooking.ST_SUBMITTED: {VendorBooking.ST_APPROVED, VendorBooking.ST_REJECTED},
    VendorBooking.ST_REJECTED: {VendorBooking.ST_DRAFT},
    VendorBooking.ST_APPROVED: {VendorBooking.ST_SENT},
    VendorBooking.ST_SENT: {VendorBooking.ST_CONFIRMED, VendorBooking.ST_CANCELLED},
    VendorBooking.ST_CONFIRMED: {VendorBooking.ST_DONE},
    VendorBooking.ST_CANCELLED: set(),
    VendorBooking.ST_DONE: set(),
}


def _transition_or_400(vb: VendorBooking, to_status: str):
    allowed = ALLOWED_TRANSITIONS.get(vb.status, set())
    if to_status not in allowed:
        raise ValueError(f"Invalid transition {vb.status} -> {to_status}")


def _redirect_update(vb_id: int, tab: str | None = None):
    url = reverse("work_orders:service_order_update", args=[vb_id])
    if tab:
        url += f"#{tab}"
    return redirect(url)


class ServiceOrderSubmitView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        vb = get_object_or_404(VendorBooking, pk=pk)
        try:
            _transition_or_400(vb, VendorBooking.ST_SUBMITTED)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        vb.status = VendorBooking.ST_SUBMITTED
        vb.submitted_at = timezone.now()
        vb.submitted_by = request.user
        vb.save(update_fields=["status", "submitted_at", "submitted_by"])
        messages.success(request, "Service Order submitted ✅")
        return _redirect_update(vb.id)


class ServiceOrderApproveView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        vb = get_object_or_404(VendorBooking, pk=pk)
        try:
            _transition_or_400(vb, VendorBooking.ST_APPROVED)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        vb.status = VendorBooking.ST_APPROVED
        vb.approved_at = timezone.now()
        vb.approved_by = request.user

        # clear reject info supaya "hilang" setelah approved
        vb.rejected_at = None
        vb.rejected_by = None
        vb.reject_reason = ""

        vb.save(update_fields=[
            "status", "approved_at", "approved_by",
            "rejected_at", "rejected_by", "reject_reason",
        ])
        messages.success(request, "Service Order approved ✅")
        return _redirect_update(vb.id)


class ServiceOrderRejectView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        vb = get_object_or_404(VendorBooking, pk=pk)
        try:
            _transition_or_400(vb, VendorBooking.ST_REJECTED)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        reason = (request.POST.get("reason") or "").strip()
        if not reason:
            messages.error(request, "Reject reason wajib diisi.")
            return _redirect_update(vb.id)

        vb.status = VendorBooking.ST_REJECTED
        vb.rejected_at = timezone.now()
        vb.rejected_by = request.user
        vb.reject_reason = reason
        vb.save(update_fields=["status", "rejected_at", "rejected_by", "reject_reason"])
        messages.warning(request, "Service Order rejected ⚠️")
        return _redirect_update(vb.id)


class ServiceOrderBackToDraftView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        vb = get_object_or_404(VendorBooking, pk=pk)
        try:
            _transition_or_400(vb, VendorBooking.ST_DRAFT)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        vb.status = VendorBooking.ST_DRAFT
        vb.save(update_fields=["status"])
        messages.success(request, "Back to Draft ✅")
        return _redirect_update(vb.id)


class ServiceOrderMarkSentView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        vb = get_object_or_404(VendorBooking, pk=pk)
        try:
            _transition_or_400(vb, VendorBooking.ST_SENT)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        vb.status = VendorBooking.ST_SENT
        vb.sent_at = timezone.now()
        vb.sent_by = request.user
        vb.sent_via = (request.POST.get("sent_via") or vb.sent_via or "").strip()
        vb.sent_to = (request.POST.get("sent_to") or vb.sent_to or "").strip()
        vb.save(update_fields=["status", "sent_at", "sent_by", "sent_via", "sent_to"])
        messages.success(request, "Service Order marked as SENT ✅")
        return _redirect_update(vb.id)


class ServiceOrderConfirmVendorView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        vb = get_object_or_404(VendorBooking, pk=pk)
        try:
            _transition_or_400(vb, VendorBooking.ST_CONFIRMED)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        vb.status = VendorBooking.ST_CONFIRMED
        vb.save(update_fields=["status"])

        # SEA only for now
        if vb.service_order_mode == "SEA":
            doc, created = _generate_sea_si_for_so(vb, issued_by=request.user)
            if created:
                messages.success(
                    request,
                    "Vendor confirmed ✅ SEA Shipping Instruction berhasil dibuat."
                )
            else:
                messages.info(
                    request,
                    "Vendor confirmed ✅ SEA Shipping Instruction sudah ada (tidak dibuat ulang)."
                )
        else:
            messages.success(
                request,
                "Vendor confirmed ✅ (Mode non-SEA: belum generate instruction)."
            )


        messages.success(request, "Vendor confirmed ✅")
        return _redirect_update(vb.id)

from django.utils import timezone
from shipments.models.shipping_instruction import ShippingInstructionDocument

class ServiceOrderCancelView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        vb = get_object_or_404(VendorBooking, pk=pk)
        try:
            _transition_or_400(vb, VendorBooking.ST_CANCELLED)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        reason = (request.POST.get("reason") or "").strip()
        if not reason:
            messages.error(request, "Cancel reason wajib diisi.")
            return _redirect_update(vb.id)

        now = timezone.now()

        vb.status = VendorBooking.ST_CANCELLED
        vb.cancelled_at = now
        vb.cancelled_by = request.user
        vb.cancel_reason = reason
        vb.save(update_fields=["status", "cancelled_at", "cancelled_by", "cancel_reason"])

        doc = getattr(vb, "shipping_instruction", None)
        if doc and doc.status != ShippingInstructionDocument.Status.CANCELLED:
            doc.status = ShippingInstructionDocument.Status.CANCELLED
            doc.cancelled_at = now
            doc.cancelled_by = request.user
            doc.save(update_fields=["status", "cancelled_at", "cancelled_by"])
            messages.info(request, "Shipping Instruction ikut di-cancel.")

        messages.warning(request, "Service Order cancelled ⚠️")
        return _redirect_update(vb.id, tab="tab-attachments")


class ServiceOrderMarkDoneView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        vb = get_object_or_404(VendorBooking, pk=pk)
        try:
            _transition_or_400(vb, VendorBooking.ST_DONE)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        vb.status = VendorBooking.ST_DONE
        vb.done_at = timezone.now()
        vb.done_by = request.user
        vb.save(update_fields=["status", "done_at", "done_by"])
        messages.success(request, "Service Order DONE ✅")
        return _redirect_update(vb.id)



from django.http import HttpResponseForbidden
class ServiceOrderOpenSeaSIView(LoginRequiredMixin, View):
    """
    Open SEA Shipping Instruction for a Service Order.
    - Guard: vb.service_order_mode == SEA
    - Guard: vb.status in (CONFIRMED, DONE)
    - Action: create doc (idempotent) then redirect to SI detail
    """

    def get(self, request, *args, **kwargs):
        vb = get_object_or_404(VendorBooking, pk=kwargs["pk"])

        if vb.service_order_mode != "SEA":
            return HttpResponseForbidden("Service Order mode is not SEA.")
        if vb.status not in ("CONFIRMED", "DONE"):
            return HttpResponseForbidden("Shipping Instruction is available only after CONFIRMED.")

        doc, _created = _generate_sea_si_for_so(vb, issued_by=request.user)

        # TODO: sesuaikan URL detail doc kamu
        # Contoh:
        return redirect("shipments:shipping_instruction_document_detail", pk=doc.pk)


def _generate_sea_si_for_so(vb: VendorBooking, issued_by):
    """
    Create SEA Shipping Instruction Document for this Service Order (idempotent).
    - OneToOne via vendor_booking
    - Also ensures SeaShippingInstructionDetail exists
    """
    doc = ShippingInstructionDocument.objects.filter(vendor_booking=vb).first()
    if doc:
        # ensure detail exists
        SeaShippingInstructionDetail.objects.get_or_create(document=doc)
        return doc, False

    letter_type = ShippingInstructionDocument.LetterType.SEA_SI
    seq = ShippingInstructionDocument.next_sequence(letter_type)

    # Required minimal fields per model: shipper_name required, others mostly blank-able :contentReference[oaicite:2]{index=2}
    doc = ShippingInstructionDocument(
        vendor_booking=vb,
        job_order=vb.job_order,
        letter_type=letter_type,
        sequence_no=seq,
        # document_no auto-filled in save() via get_next_number() :contentReference[oaicite:3]{index=3}
        shipper_name="PT Cargochains",   # TODO: ganti ambil dari Company/Config
        shipper_address="",
        customer_name="",
        customer_address="",
        reference_no=(vb.vb_number or ""),
        issued_by=issued_by,
    )
    doc.save()

    SeaShippingInstructionDetail.objects.get_or_create(document=doc)
    return doc, True
