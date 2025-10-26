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