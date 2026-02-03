from django.db import transaction
from django.utils import timezone

from shipments.models import Shipment, ShipmentEvent
from shipments.models.event import EventCode
from shipments.models.shipments import ShipmentStatus  # sesuaikan import path
from shipments.services.status_rollup import recompute_shipment_status

@transaction.atomic
def create_shipment_from_job(job, user=None):
    if not job.origin_id or not job.destination_id:
        raise ValueError("JobOrder harus punya origin & destination")

    shipment = Shipment.objects.create(
        job_order=job,
        service=job.service,
        origin=job.origin,
        destination=job.destination,
        created_by=user,
        status=ShipmentStatus.DRAFT,
    )
    # tracking_no auto di save()
    # SHIPMENT_CREATED internal auto dibuat di save()

    # public event awal supaya public tracking hidup
    ShipmentEvent.objects.get_or_create(
        shipment=shipment,
        code=EventCode.PICKUP_SCHEDULED,
        defaults={
            "event_time": timezone.now(),
            "location_text": getattr(job.origin, "name", "") or "",
            "note": "Pickup dijadwalkan",
            "is_public": True,
            "affects_status": True,
            "source": "SYSTEM",
            "created_by": user,
            "dedupe_key": f"pickup_scheduled:{shipment.pk}",
        }
    )

    recompute_shipment_status(shipment)
    return shipment
