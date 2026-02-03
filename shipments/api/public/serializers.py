from rest_framework import serializers
from shipments.models import Shipment, ShipmentEvent, ShipmentDocument

# fallback note biar timeline gak kosong
PUBLIC_EVENT_NOTE = {
    "PICKUP_SCHEDULED": "Pickup dijadwalkan",
    "PICKUP_DISPATCHED": "Kurir menuju lokasi pickup",
    "PICKUP_COMPLETED": "Pickup selesai",
    "DEPARTED": "Berangkat dari lokasi transit",
    "ARRIVED": "Tiba di lokasi transit",
    "OUTFORDELIVERY": "Sedang diantar",
    "DELIVERED": "Paket diterima",
    "EXCEPTION": "Ada kendala dalam pengiriman",
    "CANCELED": "Pengiriman dibatalkan",
}

class PublicShipmentDocumentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ShipmentDocument
        fields = ["doc_type", "url", "uploaded_at"]  # NOTE: no "note"

    def get_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class PublicShipmentEventSerializer(serializers.ModelSerializer):
    location_text = serializers.SerializerMethodField()
    note = serializers.SerializerMethodField()

    class Meta:
        model = ShipmentEvent
        fields = ["event_time", "code", "location_text", "note"]

    def get_location_text(self, obj):
        return obj.location_text or ""

    def get_note(self, obj):
        if obj.note and obj.note.strip():
            return obj.note
        return PUBLIC_EVENT_NOTE.get(obj.code, "")


class PublicShipmentTrackingSerializer(serializers.ModelSerializer):
    timeline = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    customer_ref = serializers.SerializerMethodField()
    jo_number = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    origin = serializers.SerializerMethodField()
    destination = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            "tracking_no",
            "status", 
            "timeline", 
            "documents",
          # tambahan info
            "customer_ref",
            "jo_number",
            "service",
            "origin",
            "destination",
          
        ]

    def get_timeline(self, obj):
        qs = obj.events.filter(is_public=True).order_by("event_time", "id")
        return PublicShipmentEventSerializer(qs, many=True, context=self.context).data

    def get_documents(self, obj):
        qs = obj.documents.filter(is_public=True, doc_type="POD").order_by("-uploaded_at", "-id")
        return PublicShipmentDocumentSerializer(qs, many=True, context=self.context).data

    def get_customer_ref(self, obj):
        # Shipment dulu
        v = getattr(obj, "customer_ref", None) or getattr(obj, "order_number", None)
        if v:
            return v

        # fallback JobOrder
        jo = obj.job_order
        if jo:
            return getattr(jo, "customer_ref", None) or getattr(jo, "order_number", None) or "-"
        return "-"


    def get_jo_number(self, obj):
        # Shipment dulu
        v = getattr(obj, "jo_number", None)
        if v:
            return v

        jo = obj.job_order
        if jo:
            return getattr(jo, "number", None) or getattr(jo, "jo_number", None) or "-"
        return "-"


    def get_service(self, obj):
        v = getattr(obj, "service", None) or getattr(obj, "service_type", None)
        if v:
            return str(v)

        jo = obj.job_order
        if jo:
            v2 = getattr(jo, "service", None) or getattr(jo, "service_type", None)
            return str(v2) if v2 else "-"
        return "-"


    def get_origin(self, obj):
        v = getattr(obj, "origin", None)
        if v:
            return str(v)

        jo = obj.job_order
        if jo:
            v2 = getattr(jo, "origin", None)
            return str(v2) if v2 else "-"
        return "-"


    def get_destination(self, obj):
        v = getattr(obj, "destination", None)
        if v:
            return str(v)

        jo = obj.job_order
        if jo:
            v2 = getattr(jo, "destination", None)
            return str(v2) if v2 else "-"
        return "-"
