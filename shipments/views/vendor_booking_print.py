from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from shipments.models.vendor_bookings import VendorBooking
from shipments.services.vendor_booking_calc import calc_booking_totals
from django.http import HttpResponse
from django.utils.html import escape
import traceback



LETTER_TYPE_TO_TEMPLATE = {
    "SEA_SI": "sea_si.html",
    "AIR_SLI": "air_sli.html",
    "TRUCK_TO": "truck_to.html",
}

def get_print_template(letter_type: str) -> str:
    lt = (letter_type or "").strip().upper()
    return LETTER_TYPE_TO_TEMPLATE.get(lt, "generic.html")

class VendorBookingPrintView(LoginRequiredMixin, View):
    def get(self, request, pk):
        vb = get_object_or_404(VendorBooking, pk=pk)

        tpl_name = get_print_template(vb.letter_type)
        tpl = f"vendor_bookings/print/{tpl_name}"

        header = {
            "notes": getattr(vb, "notes", "") or "-",
            "wo_notes": getattr(vb, "wo_notes", "") or "",
        }

        return render(request, tpl, {
            "vb": vb,
            "object": vb,     # kompatibel dgn template lama
            "header": header, # biar {{ header.xxx }} aman
            "totals": calc_booking_totals(vb),
            "is_draft": (vb.status == VendorBooking.ST_DRAFT),
        })




# PDF wrapper: kalau projectmu sudah punya wkhtmltopdf util, pakai itu.
class VendorBookingPdfView(LoginRequiredMixin, View):
    def get(self, request, pk):
        vb = get_object_or_404(VendorBooking, pk=pk)
        # placeholder: implement pakai util existing wkhtmltopdf
        # return wkhtmltopdf_response(request, template, context, filename)
        return VendorBookingPrintView().get(request, pk)
