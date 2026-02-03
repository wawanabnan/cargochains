from shipments.models import ShipmentStatus

STATUS_RANK = {
    ShipmentStatus.DRAFT: 10,
    ShipmentStatus.PICKUP: 20,
    ShipmentStatus.IN_TRANSIT: 30,
    ShipmentStatus.OUT_FOR_DELIVERY: 40,
    ShipmentStatus.DELIVERED: 50,
    ShipmentStatus.EXCEPTION: 90,
    ShipmentStatus.CANCELED: 99,
}

EVENT_TO_STATUS = {
    "PICKUP_SCHEDULED": ShipmentStatus.PICKUP,
    "PICKUP_DISPATCHED": ShipmentStatus.PICKUP,
    "PICKUP_COMPLETED": ShipmentStatus.IN_TRANSIT,

    "DEPARTED": ShipmentStatus.IN_TRANSIT,
    "ARRIVED": ShipmentStatus.IN_TRANSIT,

    "OUTFORDELIVERY": ShipmentStatus.OUT_FOR_DELIVERY,
    "DELIVERED": ShipmentStatus.DELIVERED,

    "EXCEPTION": ShipmentStatus.EXCEPTION,
    "CANCELED": ShipmentStatus.CANCELED,

    # none / non-affect
    "SHIPMENT_CREATED": None,
    "POD_UPLOADED": None,
    "EXCEPTION_RESOLVED": None,  # handled specially
}

def bump_status(current, target):
    if not target:
        return current
    if STATUS_RANK.get(target, 0) > STATUS_RANK.get(current, 0):
        return target
    return current

def recompute_shipment_status(shipment):
    """
    Recompute dari semua event affects_status=True agar robust.
    """
    qs = shipment.events.filter(affects_status=True).order_by("event_time", "id")

    status = ShipmentStatus.DRAFT
    for ev in qs:
        mapped = EVENT_TO_STATUS.get(ev.code)

        if ev.code == "EXCEPTION_RESOLVED":
            # balik ke status terbaik dari event sebelum exception (simple + aman)
            prev = shipment.events.filter(
                affects_status=True,
                event_time__lte=ev.event_time,
            ).exclude(code__in=["EXCEPTION", "EXCEPTION_RESOLVED"]).order_by("event_time", "id")

            tmp = ShipmentStatus.DRAFT
            for pev in prev:
                tmp = bump_status(tmp, EVENT_TO_STATUS.get(pev.code))
            mapped = tmp

        status = bump_status(status, mapped)

    if shipment.status != status:
        shipment.status = status
        shipment.save(update_fields=["status"])
    return status
