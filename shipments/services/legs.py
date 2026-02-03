# shipments/services/legs.py
from django.db import transaction
from shipments.models.leg import ShipmentLeg


SERVICE_LEG_TEMPLATES: dict[str, list[str]] = {
    "D2D_TRK": ["TRUCK"],

    "P2P_SEA": ["SEA"],
    "D2P_SEA": ["TRUCK", "SEA"],
    "P2D_SEA": ["SEA", "TRUCK"],
    "D2D_SEA": ["TRUCK", "SEA", "TRUCK"],

    "A2A_AIR": ["AIR"],
    "D2A_AIR": ["TRUCK", "AIR"],
    "A2D_AIR": ["AIR", "TRUCK"],
    "D2D_AIR": ["TRUCK", "AIR", "TRUCK"],
}

@transaction.atomic
def generate_default_legs(shipment, *, overwrite: bool = False) -> list[ShipmentLeg]:
    if not shipment.service_id:
        return []

    existing = ShipmentLeg.objects.filter(shipment=shipment).order_by("seq")
    if existing.exists():
        if not overwrite:
            return list(existing)
        existing.delete()

    code = getattr(shipment.service, "code", None)
    modes = SERVICE_LEG_TEMPLATES.get(code) or ["TRUCK"]

    # jangan bikin legs kalau lokasi belum lengkap
    if not shipment.origin_id or not shipment.destination_id:
        return []

    origin = shipment.origin
    dest = shipment.destination

    # OPTIONAL intermediates (kalau field-nya ada)
    pol = getattr(shipment, "origin_port", None)
    pod = getattr(shipment, "destination_port", None)
    aol = getattr(shipment, "origin_airport", None)
    aod = getattr(shipment, "destination_airport", None)

    # Tentukan “nodes” (titik-titik) yang akan dipakai untuk from->to
    nodes = None

    # SEA patterns
    if "SEA" in modes and pol and pod:
        if modes == ["SEA"]:
            nodes = [pol, pod]
        elif modes == ["TRUCK", "SEA"]:
            nodes = [origin, pol, pod]
        elif modes == ["SEA", "TRUCK"]:
            nodes = [pol, pod, dest]
        elif modes == ["TRUCK", "SEA", "TRUCK"]:
            nodes = [origin, pol, pod, dest]

    # AIR patterns
    if nodes is None and "AIR" in modes and aol and aod:
        if modes == ["AIR"]:
            nodes = [aol, aod]
        elif modes == ["TRUCK", "AIR"]:
            nodes = [origin, aol, aod]
        elif modes == ["AIR", "TRUCK"]:
            nodes = [aol, aod, dest]
        elif modes == ["TRUCK", "AIR", "TRUCK"]:
            nodes = [origin, aol, aod, dest]

    # fallback (MVP lama): semua leg origin->dest
    if nodes is None:
        # bikin nodes length = len(modes)+1 biar loop gampang
        nodes = [origin] + [dest] * len(modes)


    origin = shipment.origin
    dest = shipment.destination

    pol = getattr(shipment, "origin_port", None)
    pod = getattr(shipment, "destination_port", None)
    aol = getattr(shipment, "origin_airport", None)
    aod = getattr(shipment, "destination_airport", None)

    nodes = None

    # SEA
    if "SEA" in modes and pol and pod:
        if modes == ["SEA"]:
            nodes = [pol, pod]
        elif modes == ["TRUCK", "SEA"]:
            nodes = [origin, pol, pod]
        elif modes == ["SEA", "TRUCK"]:
            nodes = [pol, pod, dest]
        elif modes == ["TRUCK", "SEA", "TRUCK"]:
            nodes = [origin, pol, pod, dest]

    # AIR
    if nodes is None and "AIR" in modes and aol and aod:
        if modes == ["AIR"]:
            nodes = [aol, aod]
        elif modes == ["TRUCK", "AIR"]:
            nodes = [origin, aol, aod]
        elif modes == ["AIR", "TRUCK"]:
            nodes = [aol, aod, dest]
        elif modes == ["TRUCK", "AIR", "TRUCK"]:
            nodes = [origin, aol, aod, dest]

    # fallback (behavior lama)
    if nodes is None:
        nodes = [origin] + [dest] * len(modes)

    legs: list[ShipmentLeg] = []
    for i, mode in enumerate(modes, start=1):
        legs.append(
            ShipmentLeg(
                shipment=shipment,
                seq=i,
                mode=mode,
                from_location=nodes[i - 1],
                to_location=nodes[i],
                status="PLANNED",
            )
        )


        ShipmentLeg.objects.bulk_create(legs)
        return list(ShipmentLeg.objects.filter(shipment=shipment).order_by("seq"))
