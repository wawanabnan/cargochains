import json
from pathlib import Path
from django.conf import settings

# cache sederhana biar tidak baca file terus
_CACHE = None

def _load_json():
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    path = Path(settings.BASE_DIR) / "shipments" / "static" / "vendor_bookings" / "heading.json"
    with path.open("r", encoding="utf-8") as f:
        _CACHE = json.load(f)
    return _CACHE


def get_vendor_booking_heading(letter_type: str):
    """
    letter_type contoh:
      - SEA_SI
      - AIR_SLI
      - TRUCK_TO
    """
    cfg = _load_json().get("vendor_booking", {})
    return cfg.get(letter_type) or cfg.get("DEFAULT") or {
        "title": "Vendor Booking",
        "labels": {}
    }
