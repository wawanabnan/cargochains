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

def children_by_parent(request, parent_id: int):
    qs = Location.objects.filter(parent_id=parent_id, status="active").order_by("name").values("id","name","kind")
    return JsonResponse({"results": list(qs)})



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

    def get(self, request, *args, **kwargs):
        q = (request.GET.get("q") or request.GET.get("term") or "").strip()
        items = [self.normalize(loc) for loc in self.get_queryset(q)]
        return JsonResponse(items, safe=False)  # LIST → safe=False
    
    
    def normalize(self, loc):
        kind = getattr(loc, "kind", "") or ""
        suffix = f" [{kind}]" if kind else ""

        # --- ambil chain (sesuaikan dengan model kamu) ---
        # Opsi 1: kalau ada field eksplisit
        district = getattr(loc, "district_name", None) or getattr(loc, "district", None)
        region = getattr(loc, "region_name", None) or getattr(loc, "region", None)
        province = getattr(loc, "province_name", None) or getattr(loc, "province", None)

        # Opsi 2: kalau model hierarchical pakai parent
        # contoh: district -> parent(region) -> parent(province)
        # (jalankan hanya kalau opsi 1 kosong)
        if not (district or region or province):
            district = getattr(loc, "name", None)
            p1 = getattr(loc, "parent", None)
            p2 = getattr(p1, "parent", None) if p1 else None
            region = getattr(p1, "name", None) if p1 else None
            province = getattr(p2, "name", None) if p2 else None

        return {
            "id": loc.id,
            "label": f"{loc.name}{suffix}",
            "value": loc.name,
            "name": loc.name,
            "kind": kind,

            # ✅ tambahan untuk dipakai UI pickup
            "district": district,
            "region": region,
            "province": province,
        }


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



import re
from django.http import JsonResponse
from django.views import View
from django.db.models import Q, Case, When, IntegerField

from geo.models import Location


class LocationSelect2View(View):
    PAGE_SIZE = 20
    EXCLUDED_KINDS = {"village"}  # hanya buang village

    PORT_KINDS = {"port", "offshore-terminal"}
    AIRPORT_KINDS = {"airport"}

    # kata-kata yang dianggap "tipe", akan dibuang dari query pencarian
    STOPWORDS = {
        "kabupaten", "kab",
        "kecamatan", "kec",
        "kota", "city",
        "provinsi", "prov",
        "pelabuhan", "port",
        "bandara", "airport",
    }

    def get(self, request):
        q = (request.GET.get("q") or request.GET.get("term") or "").strip()
        page = int(request.GET.get("page") or 1)
        q_l = q.lower()

        qs = Location.objects.all().exclude(kind__in=self.EXCLUDED_KINDS)

        if not q:
            return JsonResponse({"results": [], "pagination": {"more": False}})

        # --- 1) detect tipe (optional) ---
        kind_filter = None
        if re.search(r"\b(airport|bandara)\b", q_l):
            kind_filter = self.AIRPORT_KINDS
        elif re.search(r"\b(pelabuhan|port)\b", q_l):
            kind_filter = self.PORT_KINDS
        elif re.search(r"\b(kabupaten|kab)\b", q_l):
            kind_filter = {"regency"}
        elif re.search(r"\b(kecamatan|kec)\b", q_l):
            kind_filter = {"district"}
        elif re.search(r"\b(provinsi|prov)\b", q_l):
            kind_filter = {"province"}
        elif re.search(r"\b(kota|city)\b", q_l):
            kind_filter = {"city"}

        # --- 2) bersihkan query: buang stopwords biar "kabupaten sume" jadi "sume" ---
        tokens = re.findall(r"[a-z0-9]+", q_l)
        tokens = [t for t in tokens if t not in self.STOPWORDS]
        q_clean = " ".join(tokens).strip() or q  # fallback kalau habis semua

        # --- 3) search utama pakai q_clean ---
        qs = qs.filter(
            Q(name__icontains=q_clean) |
            Q(display_name__icontains=q_clean) |
            Q(code__icontains=q_clean) |
            Q(iata_code__icontains=q_clean) |
            Q(unlocode__icontains=q_clean) |
            Q(kind__icontains=q_clean)
        )

        # apply filter tipe kalau ada
        if kind_filter:
            qs = qs.filter(kind__in=kind_filter)

        # --- 4) ranking: yang name diawali q_clean naik ke atas ---
        qs = qs.annotate(
            rank=Case(
                When(code__iexact=q_clean, then=50),
                When(iata_code__iexact=q_clean, then=45),
                When(unlocode__iexact=q_clean, then=40),
                When(name__iexact=q_clean, then=35),
                When(display_name__iexact=q_clean, then=33),
                When(name__istartswith=q_clean, then=30),
                When(display_name__istartswith=q_clean, then=25),
                When(name__icontains=q_clean, then=20),
                When(display_name__icontains=q_clean, then=15),
                default=0,
                output_field=IntegerField(),
            )
        ).order_by("-rank", "name")

        # pagination
        total = qs.count()
        start = (page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        items = qs[start:end]

        results = []
        for obj in items:
            code = (obj.iata_code or obj.unlocode or obj.code or "").strip()

            # ✅ ambil chain dari helper
            district, region, province = self.get_admin_chain(obj)

            results.append({
                "id": obj.pk,
                "text": obj.name,
                "subtext": obj.display_name or "",
                "kind": (obj.kind or "").upper(),
                "code": code,

                # ✅ tambahan untuk pickup display
                "district": district,
                "region": region,
                "province": province,
            })
                
        return JsonResponse({"results": results, "pagination": {"more": end < total}})

    def get_admin_chain(self, obj):
        """
        Try derive district/region/province from hierarchical parent
        or fallback parse display_name.
        """
        district = region = province = None

        # 1) coba via parent chain (kalau model punya parent)
        cur = obj
        while cur:
            k = (getattr(cur, "kind", "") or "").lower()
            if k == "district" and not district:
                district = cur.name
            elif k in ("city", "regency") and not region:
                region = cur.name
            elif k == "province" and not province:
                province = cur.name
            cur = getattr(cur, "parent", None)

        # 2) fallback: parse display_name "Kramat Jati, Jakarta Timur, DKI Jakarta"
        if obj.display_name:
            parts = [p.strip() for p in obj.display_name.split(",") if p.strip()]
            if parts:
                district = district or parts[0]
            if len(parts) >= 2:
                region = region or parts[1]
            if len(parts) >= 3:
                province = province or parts[2]

        # 3) last fallback
        district = district or obj.name
        return district, region, province
