# work_orders/utils/description.py

def _s(x) -> str:
    return str(x).strip() if x else ""


def _detect_leg(cost_type) -> str:
    """
    PICKUP / DELIVERY / FREIGHT
    Berdasarkan flag di CostType.
    """
    if not cost_type:
        return "FREIGHT"

    if getattr(cost_type, "pickup_trucking", False):
        return "PICKUP"

    if getattr(cost_type, "delivery_trucking", False):
        return "DELIVERY"

    return "FREIGHT"


def _route_for_service(job, service: str, leg: str) -> tuple[str, str]:
    svc = (service or "").upper()

    pickup = _s(getattr(job, "pickup", ""))
    delivery = _s(getattr(job, "delivery", ""))
    origin = _s(getattr(job, "origin", ""))
    destination = _s(getattr(job, "destination", ""))

    if svc == "D2D":
        if leg == "PICKUP":
            return pickup, origin
        if leg == "DELIVERY":
            return destination, delivery
        return origin, destination  # FREIGHT

    if svc == "P2P":
        return origin, destination

    if svc == "D2P":
        if leg == "PICKUP":
            return pickup, origin
        return "", ""

    if svc == "P2D":
        if leg == "DELIVERY":
            return destination, delivery
        return "", ""

    # fallback
    if origin or destination:
        return origin, destination
    return pickup, delivery


def build_line_description(job, job_cost) -> str:
    """
    Final description untuk Service Order Line.

    Format:
    <base_desc> | FROM → TO
    """

    ct = getattr(job_cost, "cost_type", None)

    # BASE DESCRIPTION
    base_desc = (
        _s(getattr(job_cost, "description", ""))
        or _s(getattr(ct, "name", ""))
    )

    # SERVICE
    service = _s(getattr(job, "service", ""))

    # LEG
    leg = _detect_leg(ct)

    # ROUTE
    from_loc, to_loc = _route_for_service(job, service, leg)
    route = " → ".join([x for x in [from_loc, to_loc] if x])

    if base_desc and route:
        return f"{base_desc} | {route}"

    return base_desc or route or "-"
