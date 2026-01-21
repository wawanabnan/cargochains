from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from shipments.models.vendor_bookings import VendorBooking
from shipments.services.vendor_booking_calc import calc_booking_totals

LETTER_MAP = {
    "SEA": "SI",
    "AIR": "SLI",
    "INLAND": "SO",
    "TRUCK": "SO",
}

class VendorBookingPrintView(LoginRequiredMixin, View):
    def get(self, request, pk):
        vb = get_object_or_404(VendorBooking, pk=pk)
        mode = getattr(getattr(vb, "job_order", None), "mode", "") or getattr(vb, "mode", "")
        letter = LETTER_MAP.get(mode, "WO")

        # start from SO template; later you copy for SI/SLI/WO
        tpl = f"shipments/vendor_booking/print/{letter}.html"
        return render(request, tpl, {
            "vb": vb,
            "totals": calc_booking_totals(vb),
            "is_draft": (vb.status == "DRAFT"),
        })


# PDF wrapper: kalau projectmu sudah punya wkhtmltopdf util, pakai itu.
class VendorBookingPdfView(LoginRequiredMixin, View):
    def get(self, request, pk):
        vb = get_object_or_404(VendorBooking, pk=pk)
        # placeholder: implement pakai util existing wkhtmltopdf
        # return wkhtmltopdf_response(request, template, context, filename)
        return VendorBookingPrintView().get(request, pk)
