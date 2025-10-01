
from ..models import ShipmentStatusLog

def add_status(shipment, user, status, event_time=None, note=None):
    log = ShipmentStatusLog.objects.create(
        shipment=shipment, user=user, status=status,
        event_time=event_time, note=note
    )
    shipment.status = status
    shipment.save(update_fields=["status","updated_at"])
    return log
