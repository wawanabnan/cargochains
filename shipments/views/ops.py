# shipments/views/ops.py
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shipments.models import Shipment, ShipmentDocument, ShipmentLegTrip
from shipments.services import ops
from shipments.services.event import create_event
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


from django.db import transaction

from shipments.models import ShipmentEvent
from shipments.services.status_rollup import recompute_shipment_status


@transaction.atomic
def create_event(
    *,
    shipment,
    code,
    event_time=None,
    location_text="",
    note="",
    is_public=False,
    affects_status=True,
    leg=None,
    trip=None,
    source="OPS",
    source_ref="",
    created_by=None,
    dedupe_key=None,
):
    """
    Single entry point to create ShipmentEvent from ops.
    - Applies defaults
    - Handles optional dedupe
    - Recomputes Shipment.status if affects_status=True
    """
    if event_time is None:
        event_time = timezone.now()

    # Deduping: if dedupe_key provided, don't create duplicates
    if dedupe_key:
        ev, created = ShipmentEvent.objects.get_or_create(
            shipment=shipment,
            dedupe_key=dedupe_key,
            defaults={
                "leg": leg,
                "trip": trip,
                "code": code,
                "event_time": event_time,
                "location_text": location_text or "",
                "note": note or "",
                "is_public": is_public,
                "affects_status": affects_status,
                "source": source,
                "source_ref": source_ref or "",
                "created_by": created_by,
            },
        )
        # If existing event returned, still ensure status is correct (optional)
        if ev.affects_status:
            recompute_shipment_status(shipment)
        return ev

    ev = ShipmentEvent.objects.create(
        shipment=shipment,
        leg=leg,
        trip=trip,
        code=code,
        event_time=event_time,
        location_text=location_text or "",
        is_public=is_public,
        affects_status=affects_status,
        source=source,
        source_ref=source_ref or "",
        created_by=created_by,
    )

    if ev.affects_status:
        recompute_shipment_status(shipment)

    return ev


class OpsEventSerializer(serializers.Serializer):
    event_time = serializers.DateTimeField(required=False)
    location_text = serializers.CharField(required=False, allow_blank=True, default="")
    note = serializers.CharField(required=False, allow_blank=True, default="")

@method_decorator(csrf_exempt, name="dispatch")
class TripDispatchPickupView(APIView):
    #permission_classes = [permissions.IsAuthenticated]
    permission_classes = [permissions.AllowAny]


    def post(self, request, trip_id: int):
        trip = get_object_or_404(ShipmentLegTrip, pk=trip_id)
        s = OpsEventSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        # dispatch_pickup expects event_time, location_text, note
        ops.dispatch_pickup(trip, **s.validated_data)
        return Response({"ok": True}, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name="dispatch")
class TripDepartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, trip_id: int):
        trip = get_object_or_404(ShipmentLegTrip, pk=trip_id)
        s = OpsEventSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        # mark_departed expects actual_pickup_at, location_text, note
        ops.mark_departed(
            trip,
            actual_pickup_at=s.validated_data.get("event_time"),
            location_text=s.validated_data.get("location_text", ""),
            note=s.validated_data.get("note", ""),
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name="dispatch")
class TripArriveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, trip_id: int):
        trip = get_object_or_404(ShipmentLegTrip, pk=trip_id)
        s = OpsEventSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        # mark_arrived expects actual_dropoff_at, location_text, note
        ops.mark_arrived(
            trip,
            actual_dropoff_at=s.validated_data.get("event_time"),
            location_text=s.validated_data.get("location_text", ""),
            note=s.validated_data.get("note", ""),
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)

class PODUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    note = serializers.CharField(required=False, allow_blank=True, default="")
    delivered = serializers.BooleanField(required=False, default=False)
    delivered_at = serializers.DateTimeField(required=False)


@method_decorator(csrf_exempt, name="dispatch")
class ShipmentPODUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, shipment_id: int):
        shipment = get_object_or_404(Shipment, pk=shipment_id)

        s = PODUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        f = s.validated_data["file"]
        note = s.validated_data.get("note", "")
        delivered = s.validated_data.get("delivered", False)
        delivered_at = s.validated_data.get("delivered_at")

        # 1) Create document (tanpa note karena model tidak ada)
        doc = ShipmentDocument.objects.create(
            shipment=shipment,
            doc_type="POD",
            file=f,
            is_public=True,              # atau: shipment.status == DELIVERED baru True
            uploaded_by=request.user,
        )

        # 2) Event: POD_UPLOADED (internal, no status impact)
        create_shipment_event(
            shipment=shipment,
            code="POD_UPLOADED",
            is_public=False,
            affects_status=False,
            event_time=doc.uploaded_at or timezone.now(),
            note=note,
            created_by=request.user,
            dedupe_key=f"pod_uploaded:doc:{doc.id}",
        )

        # 3) Optional: auto delivered
        if delivered:
            if delivered_at is None:
                delivered_at = timezone.now()

            create_event(
                shipment=shipment,
                code="DELIVERED",
                is_public=True,
                affects_status=True,
                event_time=delivered_at,
                note="Delivered confirmed (POD uploaded).",
                created_by=request.user,
                dedupe_key=f"delivered:pod_doc:{doc.id}",
            )

        return Response({"ok": True, "doc_id": doc.id}, status=status.HTTP_201_CREATED)
