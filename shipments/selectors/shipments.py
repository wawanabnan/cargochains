
from ..models import Shipment

def shipment_list_qs(q=None, status=None, limit=300):
    qs = Shipment.objects.select_related("origin","destination").order_by("-id")
    if q: qs = qs.filter(number__icontains=q.strip())
    if status: qs = qs.filter(status=status)
    return qs[:limit]

def shipment_detail_qs():
    return Shipment.objects.select_related(
        "origin","destination","shipper","consignee","carrier","agency"
    )
