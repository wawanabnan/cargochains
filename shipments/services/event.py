# shipments/services/events.py
from django.db import transaction, IntegrityError
from django.utils import timezone

from shipments.models import Shipment, ShipmentEvent


@transaction.atomic
def create_event(
    *,
    shipment: Shipment,
    code: str,
    event_time=None,
    is_public: bool = True,
    affects_status: bool = True,
    leg=None,
    trip=None,
    location_text: str = "",
    note: str = "",
    dedupe_key: str | None = None,
) -> ShipmentEvent:
    """
    Single entry point untuk create ShipmentEvent + idempotent dedupe + rollup status.
    """
    if event_time is None:
        event_time = timezone.now()

    # Idempotent: kalau dedupe_key sama, ambil yang sudah ada
    if dedupe_key:
        existing = ShipmentEvent.objects.filter(shipment=shipment, dedupe_key=dedupe_key).first()
        if existing:
            # tetap pastikan status up-to-date
            _rollup_status_and_update(shipment)
            return existing

    try:
        ev = ShipmentEvent.objects.create(
            shipment=shipment,
            leg=leg,
            trip=trip,
            code=code,
            event_time=event_time,
            is_public=is_public,
            affects_status=affects_status,
            location_text=location_text or "",
            note=note or "",
            dedupe_key=dedupe_key,
        )
    except IntegrityError:
        # race condition: dedupe_key unique constraint kepukul
        ev = ShipmentEvent.objects.filter(shipment=shipment, dedupe_key=dedupe_key).first()
        if not ev:
            raise

    _rollup_status_and_update(shipment)
    return ev


def _rollup_status_and_update(shipment: Shipment) -> None:
    new_status = rollup_status(shipment)
    if new_status and shipment.status != new_status:
        Shipment.objects.filter(pk=shipment.pk).update(status=new_status)


def rollup_status(shipment: Shipment) -> str:
    """
    Rule:
    - CANCELED newest -> CANCELED
    - DELIVERED newest -> DELIVERED
    - EXCEPTION newest (after last positive) -> EXCEPTION
    - else map latest positive event -> status
    - if none -> DRAFT
    """
    qs = shipment.events.filter(affects_status=True).order_by("-event_time", "-id")

    # terminal hard overrides
    if qs.filter(code="CANCELED").exists():
        # ambil yang terbaru
        latest_cancel = qs.filter(code="CANCELED").first()
        if latest_cancel:
            return "CANCELED"

    latest_delivered = qs.filter(code="DELIVERED").first()
    if latest_delivered:
        return "DELIVERED"

    latest_exception = qs.filter(code__startswith="EXCEPTION").first()
    latest_positive = qs.exclude(code__startswith="EXCEPTION").first()

    if latest_exception and (not latest_positive or latest_exception.event_time >= latest_positive.event_time):
        return "EXCEPTION"

    if not latest_positive:
        return "DRAFT"

    STATUS_EVENT_MAP = {
        "PICKUP_SCHEDULED": "PICKUP",
        "PICKUP_DISPATCHED": "PICKUP",
        "DEPARTED": "IN_TRANSIT",
        "ARRIVED": "IN_TRANSIT",
        "OUT_FOR_DELIVERY": "OUT_FOR_DELIVERY",
        "DELIVERED": "DELIVERED",
        "CANCELED": "CANCELED",
    }
    return STATUS_EVENT_MAP.get(latest_positive.code, shipment.status or "DRAFT")


from django.db import transaction
from shipments.models import ShipmentEvent
from shipments.services.status_rollup import recompute_shipment_status

@transaction.atomic
def create_shipment_event(**kwargs) -> ShipmentEvent:
    """
    Centralized event creation.
    Always use this from ops/internal endpoints to keep status consistent.
    """
    ev = ShipmentEvent.objects.create(**kwargs)

    # Only recompute if this event affects status
    if ev.affects_status:
        recompute_shipment_status(ev.shipment)

    return ev
