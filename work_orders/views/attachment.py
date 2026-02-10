# work_orders/views/service_order_attachments.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from work_orders.models.vendor_bookings import VendorBooking
from work_orders.models.vendor_bookings   import ServiceOrderAttachment


DONE_STATUSES = (VendorBooking.ST_CLOSED,)  # adjust if needed


class ServiceOrderAttachmentAddView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        so = get_object_or_404(VendorBooking, pk=pk)

        if so.status in DONE_STATUSES:
            messages.warning(request, "Service Order sudah DONE. Tidak bisa upload attachment.")
            return redirect(reverse("work_orders:service_order_update", args=[so.pk]) + "#tab-attachments")

        f = request.FILES.get("file")
        if not f:
            messages.error(request, "File wajib dipilih.")
            return redirect(reverse("work_orders:service_order_update", args=[so.pk]) + "#tab-attachments")

        ServiceOrderAttachment.objects.create(
            service_order=so,
            file=f,
            description=(request.POST.get("description") or "").strip(),
            uploaded_by=request.user,
        )
        messages.success(request, "Attachment terupload ✅")
        return redirect(reverse("work_orders:service_order_update", args=[so.pk]) + "#tab-attachments")


class ServiceOrderAttachmentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk: int, att_id: int):
        so = get_object_or_404(VendorBooking, pk=pk)

        if so.status in DONE_STATUSES:
            messages.warning(request, "Service Order sudah DONE. Tidak bisa hapus attachment.")
            return redirect(reverse("work_orders:service_order_update", args=[so.pk]) + "#tab-attachments")

        att = get_object_or_404(ServiceOrderAttachment, pk=att_id, service_order=so)
        att.delete()
        messages.success(request, "Attachment dihapus ✅")
        return redirect(reverse("work_orders:service_order_update", args=[so.pk]) + "#tab-attachments")
