from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shipments.models import Shipment
from shipments.api.public.serializers import PublicShipmentTrackingSerializer
from shipments.services.public_token import verify_public_token

class PublicTrackShipmentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, tracking_no: str):
        token = request.query_params.get("t", "")

        # token wajib
        if not token or not verify_public_token(tracking_no, token):
            return Response({"detail": "Not found."}, status=404)

        shipment = get_object_or_404(Shipment, tracking_no=tracking_no)

        # gate public: harus punya event public
        if not shipment.events.filter(is_public=True).exists():
            return Response({"detail": "Not found."}, status=404)

        serializer = PublicShipmentTrackingSerializer(
            shipment,
            context={"request": request},
        )
        return Response(serializer.data)
