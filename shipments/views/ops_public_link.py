from datetime import timedelta
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shipments.models import Shipment
from shipments.services.public_token import make_public_token
from shipments.api.internal.serializers import PublicLinkRequestSerializer

class ShipmentPublicLinkView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # ops/cs only
    
    def post(self, request, shipment_id: int):
        shipment = get_object_or_404(Shipment, pk=shipment_id)
        
        s = PublicLinkRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ttl_days = s.validated_data.get("ttl_days", 30)

        ttl_seconds = int(ttl_days) * 24 * 3600
        token = make_public_token(shipment.tracking_no, ttl_seconds=ttl_seconds)

        expires_at = timezone.now() + timedelta(days=ttl_days)

        # BASE URL: pakai domain dari request (paling aman untuk dev/staging/prod)
        base = request.build_absolute_uri("/")[:-1]  # remove trailing slash
        public_path = f"/api/public/track/{shipment.tracking_no}/?t={token}"
        url = base + public_path

        return Response(
            {
                "tracking_no": shipment.tracking_no,
                "expires_at": expires_at,
                "url": url,
            },
            status=status.HTTP_200_OK,
        )
