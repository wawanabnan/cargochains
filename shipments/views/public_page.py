from django.shortcuts import render, get_object_or_404
from shipments.models import Shipment
from shipments.api.public.serializers import PublicShipmentTrackingSerializer
from shipments.services.public_token import verify_public_token
from django.shortcuts import render, redirect
from urllib.parse import urlparse, parse_qs
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


# Label untuk badge status (customer-friendly)
PUBLIC_STATUS_LABEL = {
    "DRAFT": "Diproses",
    "PICKUP": "Pickup",
    "IN_TRANSIT": "Dalam Perjalanan",
    "OUT_FOR_DELIVERY": "Sedang Diantar",
    "DELIVERED": "Terkirim",
    "EXCEPTION": "Kendala",
    "CANCELED": "Dibatalkan",
}

# Urutan stepper sederhana (UI)
STEPPER = [
    ("PICKUP", "Pickup"),
    ("IN_TRANSIT", "Dalam Perjalanan"),
    ("OUT_FOR_DELIVERY", "Sedang Diantar"),
    ("DELIVERED", "Terkirim"),
]

# Ranking status untuk stepper highlight
STATUS_RANK = {
    "DRAFT": 0,
    "PICKUP": 1,
    "IN_TRANSIT": 2,
    "OUT_FOR_DELIVERY": 3,
    "DELIVERED": 4,
    "EXCEPTION": 99,
    "CANCELED": 99,
}


def public_tracking_page(request, tracking_no: str):
    token = (request.GET.get("t") or "").strip()
    token_ok = False
    if token:
        token_ok = verify_public_token(tracking_no, token)

    shipment = get_object_or_404(Shipment, tracking_no=tracking_no)

    # Ini tetap wajib: hanya tampil kalau ada event public (biar DRAFT gak bocor)
    if not shipment.events.filter(is_public=True).exists():
        return render(request, "public/track_processing.html", {"tracking_no": tracking_no}, status=200)

    # Kalau kamu MAU lebih ketat: tampilkan detail hanya kalau token valid
    # Tapi tetap kasih UX bagus: tampilkan halaman minta token.
    REQUIRE_TOKEN_FOR_DETAILS = False  # set True kalau mau strict
    if REQUIRE_TOKEN_FOR_DETAILS and not token_ok:
        return render(
            request,
            "shipments/public/track_need_token.html",
            {"tracking_no": tracking_no},
            status=200,
        )

    data = PublicShipmentTrackingSerializer(shipment, context={"request": request}).data

    status = data.get("status") or "DRAFT"
    status_label = PUBLIC_STATUS_LABEL.get(status, status)

    timeline = list(data.get("timeline") or [])
    timeline = sorted(timeline, key=lambda x: (x.get("event_time") or ""), reverse=True)

    documents = data.get("documents") or []
    pod = documents[0] if documents else None

    return render(
        request,
        "shipments/public/track.html",
        {
        "tracking_no": tracking_no,
        "status": status,
        "status_label": status_label,
        "timeline": timeline,
        "pod": pod,
        "token_ok": token_ok,

        # tambahan info customer-facing
        "customer_ref": data.get("customer_ref", "-"),
        "service": data.get("service", "-"),
        "origin": data.get("origin", "-"),
        "destination": data.get("destination", "-"),

        # cargo info (opsional, fallback aman)
        "cargo_name": data.get("cargo_name", "-"),
        "cargo_qty": data.get("cargo_qty", "-"),
        "cargo_weight": data.get("cargo_weight", "-"),
        },
    )

def _extract_token(token_or_link: str) -> str:
    """
    Accept either:
    - raw token: v1.12345.abcd...
    - full link: https://.../track/SHP...?t=xxxx
    - api link:  https://.../api/public/track/SHP...?t=xxxx
    Return token string or "".
    """
    s = (token_or_link or "").strip()
    if not s:
        return ""

    # If it looks like a URL, parse querystring
    if s.startswith("http://") or s.startswith("https://") or s.startswith("/"):
        try:
            # handle relative URL too
            if s.startswith("/"):
                # fake scheme/host for parsing
                s2 = "http://local" + s
            else:
                s2 = s

            qs = parse_qs(urlparse(s2).query)
            t = (qs.get("t") or [""])[0].strip()
            return t
        except Exception:
            return ""

    # Otherwise treat as raw token
    return s

def public_track_home(request):
    """
    Branded tracking landing page.
    - GET: show form
    - POST: redirect to /track/<tracking_no>/?t=<token> if provided
    """
    error = ""
    tracking_no = ""
    token_input = ""

    if request.method == "POST":
        tracking_no = (request.POST.get("tracking_no") or "").strip()
        token_input = (request.POST.get("token_or_link") or "").strip()
        token = _extract_token(token_input)

        if not tracking_no:
            error = "Nomor resi wajib diisi."
        else:
            path = reverse("shipments:public_tracking_page", kwargs={"tracking_no": tracking_no})
            if token:
                return redirect(f"{path}?t={token}")
            return redirect(path)

    return render(
        request,
        "shipments/public/track_home.html",
        {"error": error, "tracking_no": tracking_no, "token_or_link": token_input},
    )

