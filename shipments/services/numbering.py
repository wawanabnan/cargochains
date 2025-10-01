from django.utils.timezone import now
from django.db import transaction
from ..models import ShipmentNumberSequence

PREFIX = "SHP"  # ganti kalau mau

@transaction.atomic
def next_shipment_number():
    period = now().strftime("%Y%m")      # YYYYMM
    seq, _ = ShipmentNumberSequence.objects.select_for_update().get_or_create(period=period)
    seq.last_no += 1
    seq.save(update_fields=["last_no", "updated_at"])
    return f"{PREFIX}-{period}-{seq.last_no:04d}"
