# geo/views/adds.py
from django.http import JsonResponse
from django.views import View
from django.db.models import Q
from geo.models import Location  # sesuaikan kalau model-nya beda
from ..models import Location
from django.core.cache import cache  # optional, tapi aman


# geo/views/adds.py
from django.http import JsonResponse
from django.views import View
from django.db.models import Q
from geo.models import Location  # sesuaikan kalau model-nya beda

class LocationAutocompleteView(View):
    """Return JSON for autocomplete fields."""

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        if not q:
            return JsonResponse([], safe=False)

        qs = (
            Location.objects
            .filter(Q(name__icontains=q) | Q(kind__icontains=q))
            .order_by("name")[:20]
        )

        data = [
            {
                "id": obj.pk,
                "name": obj.name,
                "kind": getattr(obj, "kind", ""),
                "label": f"{obj.name}{f' [{obj.kind}]' if getattr(obj, 'kind', '') else ''}",
            }
            for obj in qs
        ]
        return JsonResponse(data, safe=False)


class LocationAjaxView(View):
    """
    Autocomplete untuk Location
    - Menerima ?q= (vanilla) atau ?term= (jQuery UI)
    - Output: list[ {id, label, value, name, kind} ]
    """
    limit = 10

    def get_queryset(self, q: str):
        qs = Location.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q))
        return qs.order_by("name")[: self.limit]

    def normalize(self, loc):
        kind = getattr(loc, "kind", "") or ""
        suffix = f" [{kind}]" if kind else ""
        return {
            "id": loc.id,                 # dipakai vanilla & untuk hidden ID
            "label": f"{loc.name}{suffix}",  # ditampilkan di dropdown
            "value": loc.name,            # jQuery UI pakai 'value'
            "name": loc.name,             # optional/informasi ekstra
            "kind": kind,                 # optional
        }

    def get(self, request, *args, **kwargs):
        q = (request.GET.get("q") or request.GET.get("term") or "").strip()
        items = [self.normalize(loc) for loc in self.get_queryset(q)]
        return JsonResponse(items, safe=False)  # LIST → safe=False
    
    

class ProvincesView(View):
    def get(self, request):
        qs = Location.objects.filter(kind="province").order_by("name")
        data = [{"id": obj.id, "name": obj.name} for obj in qs]
        return JsonResponse(data, safe=False)


class RegenciesView(View):
    def get(self, request):
        pid = request.GET.get("province_id")
        qs = Location.objects.filter(parent_id=pid, kind__in=["regency", "city"]).order_by("name")
        return JsonResponse([{"id": x.id, "name": x.name} for x in qs], safe=False)


class DistrictsView(View):
    def get(self, request):
        rid = request.GET.get("regency_id")
        qs = Location.objects.filter(parent_id=rid, kind="district").order_by("name")
        return JsonResponse([{"id": x.id, "name": x.name} for x in qs], safe=False)


class VillagesView(View):
    def get(self, request):
        did = request.GET.get("district_id")
        qs = Location.objects.filter(parent_id=did, kind="village").order_by("name")
        return JsonResponse([{"id": x.id, "name": x.name} for x in qs], safe=False)



class LocationChildrenView(View):
    def get(self, request):
        parent_id = request.GET.get("parent")
        if not parent_id:
            # Kalau nggak ada parent, balikin array kosong
            return JsonResponse([], safe=False)

        try:
            parent_id_int = int(parent_id)
        except (TypeError, ValueError):
            return JsonResponse([], safe=False)

        # Anak langsung dari parent tersebut (bisa kab/kota, kec, desa)
        qs = (
            Location.objects
            .filter(parent_id=parent_id_int)
            .order_by("name")
            .values("id", "name")  # supaya ringan, cuma ambil id & name
        )

        data = list(qs)
        return JsonResponse(data, safe=False)




