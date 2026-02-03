from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import serializers, status
from rest_framework.response import Response

from shipments.models import Shipment, ShipmentDocument, ShipmentEvent
from shipments.models.event import EventCode
from shipments.models.shipments       import ShipmentStatus  # sesuaikan import path

class PodUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    make_public = serializers.BooleanField(required=False, default=True)

class ShipmentPodUploadView(APIView):
    @transaction.atomic
    def post(self, request, tracking_no):
        shipment = Shipment.objects.get(tracking_no=tracking_no)

        ser = PodUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        is_public = bool(
            ser.validated_data.get("make_public", True)
            and shipment.status == ShipmentStatus.DELIVERED
        )

        doc = ShipmentDocument.objects.create(
            shipment=shipment,
            doc_type="POD",
            file=ser.validated_data["file"],
            is_public=is_public,
            uploaded_by=request.user if request.user.is_authenticated else None,
        )

        ShipmentEvent.objects.create(
            shipment=shipment,
            code=EventCode.POD_UPLOADED,
            event_time=timezone.now(),
            location_text="",
            note="POD uploaded",
            is_public=False,
            affects_status=False,
            source="OPS",
            created_by=request.user if request.user.is_authenticated else None,
            dedupe_key=f"pod_uploaded:{doc.pk}",
        )

        return Response(
            {
                "tracking_no": shipment.tracking_no,
                "doc_type": doc.doc_type,
                "is_public": doc.is_public,
                "uploaded_at": doc.uploaded_at,
            },
            status=status.HTTP_201_CREATED,
        )
