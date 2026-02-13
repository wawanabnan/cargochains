from django.db import transaction
from rest_framework.exceptions import ValidationError

from shipments.services import ensure_shipment_for_joborder


def _validate_ready_for_in_progress(jo):
    if not jo.service_id:
        raise ValidationError({"service": "Service wajib diisi sebelum IN_PROGRESS."})
    if not jo.origin_id:
        raise ValidationError({"origin": "Origin wajib diisi sebelum IN_PROGRESS."})
    if not jo.destination_id:
        raise ValidationError({"destination": "Destination wajib diisi sebelum IN_PROGRESS."})


@transaction.atomic
def set_joborder_status(jo, new_status: str, *, user=None):
    old_status = jo.status
    if old_status == new_status:
        return jo

    # Gate sebelum start operasi
    if new_status == jo.ST_IN_PROGRESS:
        _validate_ready_for_in_progress(jo)

    jo.status = new_status
    jo.save(update_fields=["status"])

    # ✅ Shipment dibuat saat mulai eksekusi
    if new_status == jo.ST_IN_PROGRESS:
        ensure_shipment_for_joborder(jo)

    # Optional: sync cancel/completed (boleh nyusul belakangan)
    # if new_status == jo.ST_CANCELLED and getattr(jo, "shipment", None):
    #     ...

    return jo
