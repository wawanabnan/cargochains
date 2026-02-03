# shipments/services/ops.py
from django.db import transaction
from django.utils import timezone

from shipments.models import Shipment, ShipmentLegTrip
from shipments.services.event import create_event


class OpsFlowError(ValueError):
    """Raised when operational flow is invalid (e.g., ARRIVED before DEPARTED)."""
    pass


def _last_public_event_for_trip(trip: ShipmentLegTrip):
    return (
        trip.leg.shipment.events
        .filter(trip=trip, is_public=True)
        .order_by("-event_time", "-id")
        .first()
    )


def _ensure_not_before_last_trip_event(trip: ShipmentLegTrip, event_time):
    last = _last_public_event_for_trip(trip)
    if last and event_time < last.event_time:
        raise OpsFlowError(
            f"event_time cannot be before last trip event "
            f"({last.code} at {last.event_time.isoformat()})"
        )


def _ensure_flow(trip: ShipmentLegTrip, next_code: str):
    """
    Minimal, practical flow rules:
    - ARRIVED must be after DEPARTED
    - DEPARTED cannot be after ARRIVED
    - (Optional) DEPARTED ideally after PICKUP_DISPATCHED (not enforced hard here)
    """
    last = _last_public_event_for_trip(trip)
    if not last:
        # First public event for this trip is allowed (dispatch/depart, etc.)
        return

    if next_code == "ARRIVED":
        if last.code != "DEPARTED":
            raise OpsFlowError(f"Invalid flow: ARRIVED requires last event DEPARTED, got {last.code}")

    if next_code == "DEPARTED":
        if last.code == "ARRIVED":
            raise OpsFlowError("Invalid flow: cannot DEPARTED after ARRIVED")

    if next_code == "PICKUP_DISPATCHED":
        # If already departed/arrived, don't allow dispatch
        if last.code in {"DEPARTED", "ARRIVED"}:
            raise OpsFlowError(f"Invalid flow: cannot PICKUP_DISPATCHED after {last.code}")


@transaction.atomic
def schedule_pickup(trip: ShipmentLegTrip, planned_pickup_at, location_text=""):
    trip.planned_pickup_at = planned_pickup_at
    trip.save(update_fields=["planned_pickup_at"])

    ev = create_event(
        shipment=trip.leg.shipment,
        leg=trip.leg,
        trip=trip,
        code="PICKUP_SCHEDULED",
        is_public=True,
        event_time=planned_pickup_at,
        location_text=location_text,
        dedupe_key=f"pickup_scheduled:trip:{trip.id}",
    )
    return ev


@transaction.atomic
def dispatch_pickup(trip: ShipmentLegTrip, *, event_time=None, location_text="", note=""):
    _ensure_flow(trip, "PICKUP_DISPATCHED")

    if event_time is None:
        event_time = timezone.now()

    _ensure_not_before_last_trip_event(trip, event_time)

    trip.status = "IN_PROGRESS"
    trip.save(update_fields=["status"])

    ev = create_event(
        shipment=trip.leg.shipment,
        leg=trip.leg,
        trip=trip,
        code="PICKUP_DISPATCHED",
        is_public=True,
        event_time=event_time,
        location_text=location_text,
        note=note,
        dedupe_key=f"pickup_dispatched:trip:{trip.id}",
    )
    return ev


@transaction.atomic
def mark_departed(trip: ShipmentLegTrip, *, actual_pickup_at=None, location_text="", note=""):
    _ensure_flow(trip, "DEPARTED")

    if actual_pickup_at is None:
        actual_pickup_at = timezone.now()

    _ensure_not_before_last_trip_event(trip, actual_pickup_at)

    trip.actual_pickup_at = actual_pickup_at
    trip.status = "IN_PROGRESS"
    trip.save(update_fields=["actual_pickup_at", "status"])

    ev = create_event(
        shipment=trip.leg.shipment,
        leg=trip.leg,
        trip=trip,
        code="DEPARTED",
        is_public=True,
        event_time=actual_pickup_at,
        location_text=location_text,
        note=note,
        dedupe_key=f"departed:trip:{trip.id}",
    )

    # Optional: kalau ini trip terakhir (last-mile), auto OUT_FOR_DELIVERY
    if _is_last_mile_trip(trip):
        create_event(
            shipment=trip.leg.shipment,
            leg=trip.leg,
            trip=trip,
            code="OUT_FOR_DELIVERY",
            is_public=True,
            event_time=actual_pickup_at,
            location_text=location_text,
            dedupe_key=f"ofd:trip:{trip.id}",
        )

    return ev


@transaction.atomic
def mark_arrived(trip: ShipmentLegTrip, *, actual_dropoff_at=None, location_text="", note=""):
    _ensure_flow(trip, "ARRIVED")

    if actual_dropoff_at is None:
        actual_dropoff_at = timezone.now()

    _ensure_not_before_last_trip_event(trip, actual_dropoff_at)

    trip.actual_dropoff_at = actual_dropoff_at
    trip.status = "COMPLETED"
    trip.save(update_fields=["actual_dropoff_at", "status"])

    ev = create_event(
        shipment=trip.leg.shipment,
        leg=trip.leg,
        trip=trip,
        code="ARRIVED",
        is_public=True,
        event_time=actual_dropoff_at,
        location_text=location_text,
        note=note,
        dedupe_key=f"arrived:trip:{trip.id}",
    )
    return ev


@transaction.atomic
def mark_out_for_delivery(shipment: Shipment, *, event_time=None, location_text="", note=""):
    """
    Manual OFD (optional). Kalau kamu sudah auto OFD dari last-mile departed,
    fungsi ini tetap berguna untuk edge-case (re-dispatch last mile).
    """
    if event_time is None:
        event_time = timezone.now()

    ev = create_event(
        shipment=shipment,
        code="OUT_FOR_DELIVERY",
        is_public=True,
        event_time=event_time,
        location_text=location_text,
        note=note,
        dedupe_key=f"ofd:shipment:{shipment.id}",
    )
    return ev


@transaction.atomic
def mark_delivered(shipment: Shipment, *, event_time=None, location_text="", note=""):
    """
    Delivered tanpa POD (karena kamu pilih policy #1).
    """
    if event_time is None:
        event_time = timezone.now()

    ev = create_event(
        shipment=shipment,
        code="DELIVERED",
        is_public=True,
        event_time=event_time,
        location_text=location_text,
        note=note,
        dedupe_key=f"delivered:shipment:{shipment.id}",
    )
    return ev


def _is_last_mile_trip(trip: ShipmentLegTrip) -> bool:
    """
    Simple heuristic:
    - trip berada di leg terakhir shipment, dan mode TRUCK (last mile)
    """
    shipment = trip.leg.shipment
    last_leg = shipment.legs.order_by("-seq").first()
    if not last_leg:
        return False
    return trip.leg_id == last_leg.id and last_leg.mode == "TRUCK"
