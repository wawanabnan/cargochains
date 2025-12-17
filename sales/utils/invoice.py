def build_invoice_description_from_job(job):
    """
    Description invoice line dari JobOrder:
    - cargo_description
    - pickup → delivery
    """
    parts = []

    if getattr(job, "cargo_description", None):
        parts.append(job.cargo_description.strip())

    pickup = getattr(job, "pick_up", "") or ""
    delivery = getattr(job, "delivery", "") or ""
    route = " → ".join([p for p in [pickup, delivery] if p])

    if route:
        parts.append(route)

    return "\n".join(parts)
