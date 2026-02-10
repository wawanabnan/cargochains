from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from shipments.models.vendor_bookings import VendorBooking

class VendorBookingObjectMixin(LoginRequiredMixin):
    model = VendorBooking
    context_object_name = "booking"

    def get_queryset(self):
        return (
            VendorBooking.objects
            .select_related("vendor", "currency", "job_order", "created_by")
            .prefetch_related("lines")
        )

    def get_object(self, queryset=None):
        return super().get_object(queryset=queryset)
