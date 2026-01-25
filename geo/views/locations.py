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


from django.http import JsonResponse
from django.views import View
from django.db.models import Q
import re


class LocationSelect2View2(View):
    # kind yang boleh tampil (ubah sesuai kebutuhan om)
    ALLOWED_KINDS = {"city", "airport", "seaport"}   # <- whitelist paling aman
    EXCLUDED_KINDS = {"village"}                    # optional tambahan

    def _find_ancestor_name(self, node, target_kind: str) -> str:
        """Naik ke parent sampai ketemu kind tertentu, balikin name-nya."""
        cur = node
        while cur is not None:
            if (cur.kind or "").lower() == target_kind:
                return cur.name
            cur = cur.parent
        return ""

    def _build_text(self, obj: Location) -> str:
        kind = (obj.kind or "").lower()

        # region: Province - City
        province = self._find_ancestor_name(obj, "province")
        # city kadang node itu sendiri (kalau kind=city), atau ancestor city (kalau airport/seaport anak city)
        city = obj.name if kind == "city" else self._find_ancestor_name(obj, "city")

        region = " - ".join([x for x in [province, city] if x])

        # nama utama: kalau airport/seaport, pakai obj.name; kalau city juga obj.name (udah)
        main_name = obj.name

        # code tampil: prioritaskan iata_code, lalu unlocode, lalu code
        code = (obj.iata_code or obj.unlocode or obj.code or "").strip()

        text = main_name
        if region:
            text = f"{region} • {text}"
        if code:
            text = f"{text} ({code})"

        return text

    def get(self, request):
        q = (request.GET.get("q") or request.GET.get("term") or "").strip()
        page = int(request.GET.get("page") or 1)
        page_size = 20

        if not q:
            return JsonResponse({"results": [], "pagination": {"more": False}})

        qs = Location.objects.filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(iata_code__icontains=q) | Q(unlocode__icontains=q)
        )

        # ✅ whitelist kind (paling aman agar village ga pernah muncul)
        qs = qs.filter(kind__in=self.ALLOWED_KINDS)

        # ✅ optional extra guard
        qs = qs.exclude(kind__in=self.EXCLUDED_KINDS)

        qs = qs.select_related("parent").order_by("name")

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size

        items = qs[start:end]

        results = []
        for obj in items:
            results.append({
                "id": obj.pk,
                "text": self._build_text(obj),
                "kind": (obj.kind or "").upper(),  # untuk badge
            })

        return JsonResponse({"results": results, "pagination": {"more": end < total}})




class LocationSelect2View_lama(View):
    PAGE_SIZE = 20
    ALLOWED_KINDS = {"city", "airport", "seaport"}

    def get(self, request):
        q = (request.GET.get("q") or request.GET.get("term") or "").strip()
        page = int(request.GET.get("page") or 1)

        # jangan munculin semua kalau kosong
        if not q:
            return JsonResponse({"results": [], "pagination": {"more": False}})

        q_l = q.lower()

        # kind shortcut: airport / bandara
        if q_l in {"airport", "bandara"}:
            qs = Location.objects.filter(kind__iexact="airport")

        # kind shortcut: port / pelabuhan / seaport -> seaport
        elif q_l in {"port", "pelabuhan", "seaport"}:
            qs = Location.objects.filter(kind__iexact="seaport")

        else:
            qs = Location.objects.filter(
                Q(name__icontains=q) |
                Q(kind__icontains=q) |
                Q(code__icontains=q) |
                Q(iata_code__icontains=q) |
                Q(unlocode__icontains=q)
            )

        # whitelist biar village ga ikut
        qs = qs.filter(kind__in=self.ALLOWED_KINDS).order_by("name")

        total = qs.count()
        start = (page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        items = qs[start:end]

        results = []
        for obj in items:
            code = (obj.iata_code or obj.unlocode or obj.code or "").strip()
            results.append({
                "id": obj.pk,
                "text": obj.name,
                "kind": (obj.kind or "").upper(),
                "code": code,
                "subtext": ""
            })

        return JsonResponse({
            "results": results,
            "pagination": {"more": end < total}
        })




import re
from django.http import JsonResponse
from django.views import View
from django.db.models import Q


class LocationSelect2View_lama_lama(View):
    PAGE_SIZE = 20
    ALLOWED_KINDS = {"city", "airport", "seaport"}

    def get(self, request):
        q = (request.GET.get("q") or request.GET.get("term") or "").strip()
        page = int(request.GET.get("page") or 1)
        q_l = q.lower()

        qs = Location.objects.filter(kind__in=self.ALLOWED_KINDS)

        # kalau kosong, kosongin (biar gak random)
        if not q:
            return JsonResponse({"results": [], "pagination": {"more": False}})

        # ===== SMART DETECTION (boleh ada kata tambahan) =====
        # airport keywords
        is_airport = re.search(r"\b(airport|bandara)\b", q_l) is not None
        # seaport keywords (port/pelabuhan/seaport)
        is_seaport = re.search(r"\b(pelabuhan|seaport|port)\b", q_l) is not None

        # Prioritas: kalau user nulis "airport" dan "port" bareng (mis. "air port"),
        # anggap AIRPORT (biar gak salah)
        if is_airport:
            qs = qs.filter(kind__iexact="airport")
        elif is_seaport:
            qs = qs.filter(kind__iexact="seaport")
        else:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(display_name__icontains=q) |
                Q(code__icontains=q) |
                Q(iata_code__icontains=q) |
                Q(unlocode__icontains=q) |
                Q(kind__icontains=q)
            )

        qs = qs.order_by("name")

        total = qs.count()
        start = (page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        items = qs[start:end]

        results = []
        for obj in items:
            code = (obj.iata_code or obj.unlocode or obj.code or "").strip()
            results.append({
                "id": obj.pk,
                "text": obj.name,
                "kind": (obj.kind or "").upper(),
                "code": code,
                "subtext": "",  # optional
            })

        return JsonResponse({"results": results, "pagination": {"more": end < total}})




class LocationSelect2View_lamalamalama(View):
    PAGE_SIZE = 20

    EXCLUDED_KINDS = {"village"}
    PORT_KINDS = {"port", "offshore-terminal"}
    AIRPORT_KINDS = {"airport"}

    def get(self, request):
        q = (request.GET.get("q") or request.GET.get("term") or "").strip()
        page = int(request.GET.get("page") or 1)
        q_l = q.lower()

        qs = Location.objects.all().exclude(kind__in=self.EXCLUDED_KINDS)

        if not q:
            return JsonResponse({"results": [], "pagination": {"more": False}})

        # =====================================================
        # <<< BAGIAN DETEKSI KEYWORD (INI NOMOR 3 YANG OM TANYA)
        # =====================================================

        is_airport = re.search(r"\b(airport|bandara)\b", q_l) is not None
        is_port = re.search(r"\b(pelabuhan|port)\b", q_l) is not None

        is_regency  = re.search(r"\b(kabupaten|kab)\b", q_l) is not None
        is_district = re.search(r"\b(kecamatan|kec)\b", q_l) is not None
        is_province = re.search(r"\b(provinsi|prov)\b", q_l) is not None
        is_city     = re.search(r"\b(kota|city)\b", q_l) is not None

        # =====================================================
        # APPLY FILTER BERDASARKAN KEYWORD
        # =====================================================

        if is_airport:
            qs = qs.filter(kind__in=self.AIRPORT_KINDS)

        elif is_port:
            qs = qs.filter(kind__in=self.PORT_KINDS)

        elif is_regency:
            qs = qs.filter(kind="regency")

        elif is_district:
            qs = qs.filter(kind="district")

        elif is_province:
            qs = qs.filter(kind="province")

        elif is_city:
            qs = qs.filter(kind="city")

        else:
            # fallback search normal
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(display_name__icontains=q) |
                Q(code__icontains=q) |
                Q(iata_code__icontains=q) |
                Q(unlocode__icontains=q) |
                Q(kind__icontains=q)
            )

        qs = qs.order_by("name")

        # =====================================================
        # PAGINATION + RESPONSE
        # =====================================================

        total = qs.count()
        start = (page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        items = qs[start:end]

        results = []
        for obj in items:
            code = (obj.iata_code or obj.unlocode or obj.code or "").strip()
            results.append({
                "id": obj.pk,
                "text": obj.name,
                "kind": (obj.kind or "").upper(),
                "code": code,
                "subtext": "",
            })

        return JsonResponse({
            "results": results,
            "pagination": {"more": end < total}
        })




import re
from django.http import JsonResponse
from django.views import View
from django.db.models import Q

from geo.models import Location  # ✅ ini yang benar


class LocationSelect2ViewOldOld(View):
    PAGE_SIZE = 20
    EXCLUDED_KINDS = {"village"}  # sesuai kebutuhan

    def get(self, request):
        q = (request.GET.get("q") or request.GET.get("term") or "").strip()
        page = int(request.GET.get("page") or 1)
        q_l = q.lower()

        qs = Location.objects.all().exclude(kind__in=self.EXCLUDED_KINDS)

        if not q:
            return JsonResponse({"results": [], "pagination": {"more": False}})

        # keyword kind -> jadi filter tambahan (bukan pengganti search)
        kind_whitelist = None
        if re.search(r"\b(airport|bandara)\b", q_l):
            kind_whitelist = {"airport"}
        elif re.search(r"\b(pelabuhan|port)\b", q_l):
            kind_whitelist = {"port", "offshore-terminal"}  # ✅ dari hasil query om
        elif re.search(r"\b(kabupaten|kab)\b", q_l):
            kind_whitelist = {"regency"}
        elif re.search(r"\b(kecamatan|kec)\b", q_l):
            kind_whitelist = {"district"}
        elif re.search(r"\b(provinsi|prov)\b", q_l):
            kind_whitelist = {"province"}
        elif re.search(r"\b(kota|city)\b", q_l):
            kind_whitelist = {"city"}

        # ✅ always search by name/alias/kode
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(display_name__icontains=q) |
            Q(code__icontains=q) |
            Q(iata_code__icontains=q) |
            Q(unlocode__icontains=q)
        )

        # ✅ apply kind filter only if keyword type detected
        if kind_whitelist:
            qs = qs.filter(kind__in=kind_whitelist)

        qs = qs.order_by("name")

        total = qs.count()
        start = (page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        items = qs[start:end]

        results = []
        for obj in items:
            code = (obj.iata_code or obj.unlocode or obj.code or "").strip()
            results.append({
                "id": obj.pk,
                "text": obj.name,
                "subtext": obj.display_name or "",  # ✅ ini bikin “Kabupaten Sumedang, Jawa Barat”
                "kind": (obj.kind or "").upper(),
                "code": code,
            })

        return JsonResponse({"results": results, "pagination": {"more": end < total}})




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
            results.append({
                "id": obj.pk,
                "text": obj.name,
                "subtext": obj.display_name or "",
                "kind": (obj.kind or "").upper(),
                "code": code,
            })

        return JsonResponse({"results": results, "pagination": {"more": end < total}})
