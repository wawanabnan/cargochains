from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from shipments.models.vendor_bookings import VendorBooking
from shipments.services.vendor_booking_calc import calc_booking_totals

class VendorBookingConfirmView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk):
        vb = get_object_or_404(VendorBooking, pk=pk)

        if vb.status != "DRAFT":
            messages.info(request, "Sudah confirmed.")
            return redirect(reverse("shipments:vendor_booking_edit", args=[vb.pk]))

        # recalc sekali lagi sebelum lock
        t = calc_booking_totals(vb)
        vb.total_amount = t["total_amount"]
        vb.wht_amount = t["wht_amount"]

        vb.status = "CONFIRMED"
        vb.save(update_fields=["status", "total_amount", "wht_amount"])

        messages.success(request, "Vendor Booking CONFIRMED ✅")
        return redirect(reverse("shipments:vendor_booking_edit", args=[vb.pk]))


