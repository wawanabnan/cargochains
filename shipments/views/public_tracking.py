from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework import status as http_status

from shipments.models import Shipment, ShipmentEvent


CODE_ALIASES = {
    "OUTFORDELIVERY": "OUT_FOR_DELIVERY",
    # kalau ada varian lain, tambah di sini
    # "OFD": "OUT_FOR_DELIVERY",
}


class PublicTrackAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_track"

    def get(self, request, tracking_no: str):
        shipment = Shipment.objects.filter(tracking_no=tracking_no).first()
        if not shipment:
            return Response(
                {"detail": "Tracking number not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        events = (
            ShipmentEvent.objects
            .filter(shipment=shipment, is_public=True)
            .order_by("event_time", "id")
        )

        # ✅ DEDUPE (hapus event double yang persis sama)
        seen = set()
        timeline = []
        best = {}  # key -> event dict

        for e in events:
            code = CODE_ALIASES.get(e.code, e.code)
            location_text = e.location_text or ""
            note = e.note or ""

            # dedupe signature untuk public: code + event_time + location_text
            key = (code, e.event_time, location_text)

            candidate = {
                "code": code,
                "event_time": e.event_time,
                "location_text": location_text,
                "note": note,
            }

            if key not in best:
                best[key] = candidate
            else:
                # pilih yang note lebih informatif
                if len(candidate["note"]) > len(best[key]["note"]):
                    best[key] = candidate

        timeline = list(best.values())
        timeline.sort(key=lambda x: (x["event_time"], x["code"]))

        return Response(
            {
                "tracking_no": shipment.tracking_no,
                "status": shipment.status,
                "timeline": timeline,
            },
            status=http_status.HTTP_200_OK,
        )
