# shipments/services.py
from shipments.models import Shipment

def ensure_shipment_for_joborder(jo) -> Shipment:
    # kalau sudah ada, langsung return
    shipment = getattr(jo, "shipment", None)
    if shipment:
        return shipment

    # validasi minimal untuk bikin legs (boleh tetap bikin shipment meski origin/dest null,
    # tapi kamu bilang cocoknya saat mulai operasi, biasanya sudah lengkap)
    shipment = Shipment(
        job_order=jo,
        service=jo.service,
        origin=jo.origin,
        destination=jo.destination,
        status="DRAFT",
    )
    shipment.save()  # triggers tracking_no + auto legs (kalau origin/dest ada) + private SHIPMENT_CREATED
    return shipment
