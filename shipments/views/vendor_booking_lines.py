import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.generic import View

from shipments.models.vendor_bookings import VendorBookingLine
from shipments.views.vendor_booking_base import VendorBookingObjectMixin
from shipments.services.vendor_booking_line_services import apply_vendor_booking_line


class VendorBookingLineDetailsView(VendorBookingObjectMixin, View):
    """
    GET  -> return JSON detail line (untuk open modal)
    POST -> save line dari modal (cost_type + details + qty/uom + optional manual desc)
    """

    def get(self, request, pk):
        line = VendorBookingLine.objects.select_related("booking", "cost_type").get(pk=pk)
        b = line.booking

        return JsonResponse({
            "ok": True,
            "line": {
                "id": line.id,
                "booking_id": b.id,
                "line_no": line.line_no,
                "cost_type_id": line.cost_type_id,
                "service_type": line.service_type,
                "description": line.description,
                "description_is_manual": line.description_is_manual,
                "qty": str(line.qty) if line.qty is not None else "",
                "uom": line.uom or "",
                "details": line.details or {},
            }
        })

    def post(self, request, pk):
        line = VendorBookingLine.objects.select_related("booking").get(pk=pk)
        b = line.booking

        if b.status != b.ST_DRAFT:
            return HttpResponseForbidden("Booking bukan DRAFT, line tidak bisa diubah.")

        try:
            cost_type_id = int(request.POST.get("cost_type_id") or 0)
            details = json.loads(request.POST.get("details_json") or "{}")
            qty = request.POST.get("qty")
            qty = float(qty) if qty not in (None, "",) else None
            uom = request.POST.get("uom") or ""
            desc_manual = request.POST.get("description_manual")  # boleh kosong
        except Exception as e:
            return HttpResponseBadRequest(str(e))

        apply_vendor_booking_line(
            line,
            cost_type_id=cost_type_id,
            details=details,
            qty=qty,
            uom=uom,
            description_manual=desc_manual,
        )

        return JsonResponse({
            "ok": True,
            "line": {
                "id": line.id,
                "description": line.description,
                "service_type": line.service_type,
                "qty": str(line.qty) if line.qty is not None else "",
                "uom": line.uom or "",
                "details": line.details or {},
            }
        })
