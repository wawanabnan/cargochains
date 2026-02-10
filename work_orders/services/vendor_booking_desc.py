def _fmt_route(a, b):
    a = (a or "").strip()
    b = (b or "").strip()
    if a and b:
        return f"{a} → {b}"
    return a or b or ""

def _num(v):
    if v in (None, "", 0):
        return ""
    try:
        s = str(v)
        return s.rstrip("0").rstrip(".")
    except Exception:
        return str(v)

def build_vendor_booking_description(service_type: str, cost_type_name: str, details: dict) -> str:
    service_type = (service_type or "").upper().strip()
    cost_type_name = (cost_type_name or "").strip()
    d = details or {}

    origin = d.get("origin") or ""
    dest = d.get("destination") or ""
    route = _fmt_route(origin, dest)

    cargo = d.get("cargo_detail") or d.get("cargo") or {}
    w = cargo.get("weight")
    v = cargo.get("volume")
    cargo_str = " ".join([x for x in [f"{_num(w)} kg" if w else "", f"{_num(v)} cbm" if v else ""] if x]).strip()

    if service_type == "TRUCK":
        truck_type = (d.get("truck_type") or "").upper()
        bits = ["TRUCK"]
        if truck_type: bits.append(truck_type)
        if route: bits.append(route)
        if cargo_str: bits.append(cargo_str)
        if cost_type_name: bits.append(f"({cost_type_name})")
        return " | ".join(bits)

    if service_type == "SEA":
        pol = d.get("pol") or ""
        pod = d.get("pod") or ""
        route2 = _fmt_route(pol, pod)
        container = (d.get("container") or d.get("container_type") or "").upper()
        bits = ["SEA"]
        if container: bits.append(container)
        if route2: bits.append(route2)
        if cargo_str: bits.append(cargo_str)
        if cost_type_name: bits.append(f"({cost_type_name})")
        return " | ".join(bits)

    if service_type == "AIR":
        aol = d.get("aol") or ""
        aod = d.get("aod") or ""
        route2 = _fmt_route(aol, aod)
        chw = d.get("chargeable_weight")
        bits = ["AIR"]
        if route2: bits.append(route2)
        if chw: bits.append(f"CHW {_num(chw)} kg")
        elif cargo_str: bits.append(cargo_str)
        if cost_type_name: bits.append(f"({cost_type_name})")
        return " | ".join(bits)

    # fallback
    if route:
        return f"{cost_type_name} | {route}".strip(" |")
    return cost_type_name or "Service"
