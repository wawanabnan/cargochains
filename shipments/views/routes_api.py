# shipments/views/routes_api.py
from django.http import JsonResponse
from shipments.models .shipments import TransportationAsset

def assets_by_type(request, type_id):
    qs = TransportationAsset.objects.filter(type_id=type_id, active=True).order_by("identifier")
    data = [{"id": a.id, "name": a.identifier} for a in qs]
    return JsonResponse(data, safe=False)
