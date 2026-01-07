# shipments/services.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Iterable
from django.db import transaction
from django.utils import timezone

from shipments.models.shipments import Shipment, ShipmentRoute, TransportationType, TransportationAsset
from shipments.utils import next_shipment_number
from geo.models import Location

# NOTE: sesuaikan import model SO kamu
from sales import models as sm


# --- PATCH: cargo rollup helper ---
def _cargo_rollup(so) -> dict:
    """
    Balikkan ringkasan cargo dari Sales Order:
      {
        "description": str,           # prioritas: header so.cargo_description -> rangkum 3 line -> "General cargo"
        "qty": int|float|None,
        "weight": float|None,         # kg
        "volume": float|None,         # cbm
      }
    Null-safe dan toleran variasi field di lines (qty/quantity, weight_kg/weight_per_unit_kg, volume_cbm/volume_per_unit_cbm).
    """
    header_desc = (getattr(so, "cargo_description", "") or "").strip()

    # Ambil lines (aman kalau related_name 'lines' tidak ada)
    try:
        lines_mgr = getattr(so, "lines", None)
        lines = list(lines_mgr.all()) if hasattr(lines_mgr, "all") else []
    except Exception:
        lines = []

    total_qty = 0
    total_weight = 0.0
    total_volume = 0.0
    desc_rows = []
    max_rows = 3

    for ln in lines:
        qty = getattr(ln, "qty", None)
        if qty is None:
            qty = getattr(ln, "quantity", 0) or 0

        uom = (
            getattr(getattr(ln, "uom", None), "name", None)
            or getattr(ln, "uom_name", None)
            or ""
        )

        w = getattr(ln, "weight_kg", None)
        if w is None:
            w_unit = getattr(ln, "weight_per_unit_kg", None)
            if w_unit is not None and qty:
                w = (w_unit or 0) * (qty or 0)
        if w is None:
            w = 0

        v = getattr(ln, "volume_cbm", None)
        if v is None:
            v_unit = getattr(ln, "volume_per_unit_cbm", None)
            if v_unit is not None and qty:
                v = (v_unit or 0) * (qty or 0)
        if v is None:
            v = 0

        name = (
            getattr(ln, "description", None)
            or getattr(ln, "product_name", None)
            or getattr(ln, "item_name", None)
            or "-"
        )

        try: total_qty += (qty or 0)
        except Exception: pass
        try: total_weight += float(w or 0)
        except Exception: pass
        try: total_volume += float(v or 0)
        except Exception: pass

        if len(desc_rows) < max_rows:
            parts = [f"{name} — {qty or 0} {uom}".strip()]
            if (w or 0) > 0: parts.append(f"{float(w):g} kg")
            if (v or 0) > 0: parts.append(f"{float(v):g} cbm")
            desc_rows.append(", ".join(parts))

    if header_desc:
        description = header_desc
    elif desc_rows:
        if len(lines) > max_rows:
            desc_rows.append(f"(+{len(lines)-max_rows} more...)")
        description = "\n".join(desc_rows)
    else:
        description = "General cargo"

    return {
        "description": description,
        "qty": total_qty or getattr(so, "qty", None),
        "weight": round(total_weight, 3) if total_weight else (getattr(so, "weight", None) or 0),
        "volume": round(total_volume, 3) if total_volume else (getattr(so, "volume", None) or 0),
    }

@dataclass
class GenerateShipmentOptions:
    set_status: str = "DRAFT"    # atau "DRAFT"
    infer_mode_from_type: bool = True  # isi shipment.mode dari route.transportation_type.mode kalau tersedia


@transaction.atomic
def create_shipment_from_sales_order(
    so: sm.SalesOrder, *, user=None, opts: GenerateShipmentOptions | None = None
) -> Shipment:
    """
    Buat Shipment + ShipmentRoute dari Sales Order.
    Asumsi: SO punya lines dengan origin/destination (mirip quotation).
    """
    opts = opts or GenerateShipmentOptions()

    # Idempotency: kalau sudah pernah dibuat, kembalikan yang ada
    existing = Shipment.objects.filter(so_number=so.number).order_by("-id").first()
    if existing:
        return existing

    # --- Tentukan origin/destination header ---
    # Ambil dari line pertama yang valid; kalau tidak ada, fallback ke header (kalau tersedia)
    origin = destination = None
    origin_text = destination_text = None

    for ln in getattr(so, "lines", []).all() if hasattr(so, "lines") else []:
        if ln.origin_id and ln.destination_id:
            origin = ln.origin
            destination = ln.destination
            origin_text = getattr(ln, "origin_text", None) or ln.origin.name
            destination_text = getattr(ln, "destination_text", None) or ln.destination.name
            break

     # >>> PATCH: hitung ringkasan cargo di sini
    cargo = _cargo_rollup(so)
    # <<< PATCH
    # 
            
    # --- Buat Shipment header ---
    shp = Shipment(
        number=next_shipment_number(timezone.localdate()),
        sales_order=so,  
        so_number=so.number,
        sales_order_snap={
            "number": so.number,
            "customer_id": getattr(so.customer, "id", None),
            "customer_name": getattr(so.customer, "name", None),
            "currency": _to_snap(getattr(so, "currency", None)),
            "total_amount": str(getattr(so, "total_amount", "") or ""),
            "date": str(getattr(so, "date", "") or ""),
        },

        status=opts.set_status,
        origin=origin or getattr(so, "origin", None),
        destination=destination or getattr(so, "destination", None),
        origin_text=origin_text or getattr(so, "origin_text", None),
        destination_text=destination_text or getattr(so, "destination_text", None),

        # Parties (sesuaikan dengan field di SO kamu)
        #customer=getattr(so, "customer", None),
        shipper=getattr(so, "shipper", None) or getattr(so, "customer", None),
        consignee=getattr(so, "consignee", None),
        carrier=getattr(so, "carrier", None),
        agency=getattr(so, "agency", None),
        
         # >>> PATCH: gunakan hasil rollup (bukan getattr langsung)
        cargo_description=cargo["description"],
        weight=cargo["weight"],
        volume=cargo["volume"],
        qty=cargo["qty"],
        # <<< PATCH

        # Ringkasan kargo (opsional)
        #cargo_description=getattr(so, "cargo_description", None),
        #weight=getattr(so, "weight", None),
        #volume=getattr(so, "volume", None),
        #qty=getattr(so, "qty", None),

        # Jadwal header (optional)
        etd=getattr(so, "etd", None),
        eta=getattr(so, "eta", None),

        # Financial ringkas (opsional)
        currency=getattr(so, "currency", "IDR"),
        total=getattr(so, "total_amount", None),
    )
    shp.save()  # signals/save() akan isi snapshot *_snap dan *_text jika kosong

    # --- Buat ShipmentRoute per baris SO yang punya pair origin/destination ---
    order_no = 1
    for ln in getattr(so, "lines", []).all() if hasattr(so, "lines") else []:
        o = getattr(ln, "origin", None)
        d = getattr(ln, "destination", None)
        if not (o and d):
            continue

        # transport (opsional) — kalau SO line sudah menyimpan tipe/asset
        ttype = getattr(ln, "transportation_type", None)
        tasset = getattr(ln, "transportation_asset", None)

        route = ShipmentRoute(
            shipment=shp,
            order=order_no,
            origin=o, destination=d,
            origin_text=getattr(ln, "origin_text", "") or o.name,
            destination_text=getattr(ln, "destination_text", "") or d.name,
            planned_departure=getattr(ln, "etd", None),
            planned_arrival=getattr(ln, "eta", None),
            distance_km=getattr(ln, "distance_km", None),

            transportation_type=ttype,
            transportation_type_text=getattr(ttype, "name", "") if ttype else "",
            transportation_asset=tasset,
            transportation_asset_text=getattr(tasset, "identifier", "") if tasset else "",
            status="PLANNED",
        )
        route.save()  # snapshot lokasi & transport akan diisi di save()

        order_no += 1

    # Flag multimodal jika lebih dari satu route
    shp.is_multimodal = shp.routes.count() > 1
    if opts.infer_mode_from_type:
        # isi shipment.mode dari leg pertama yang punya tipe
        first_with_type = shp.routes.filter(transportation_type__isnull=False).order_by("order").first()
        if first_with_type:
            shp.mode = first_with_type.transportation_type.mode
    shp.save(update_fields=["is_multimodal", "mode"])

    return shp

def _to_snap(val):
    from decimal import Decimal
    from datetime import date, datetime
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    # djmoney / custom Currency object
    if hasattr(val, "code"):   # e.g. Money.currency or Currency
        return val.code
    return str(val)  


def _cargo_summary_from_so(so):
    # 1) kalau header SO sudah punya description → pakai itu
    desc = getattr(so, "cargo_description", "") or ""
    if desc.strip():
        return desc.strip()

    # 2) fallback: rangkum dari line description (maks 3 baris)
    try:
        lines = list(getattr(so, "lines", []).all()[:3])
    except Exception:
        lines = []
    if lines:
        parts = []
        for ln in lines:
            txt = (getattr(ln, "description", "") or "").strip()
            if txt:
                parts.append(txt)
        if parts:
            tail = "…" if getattr(so, "lines", []).count() > 3 else ""
            return " | ".join(parts) + tail

    # 3) fallback terakhir
    return "General cargo"

    # saat membuat Shipment:
    shp = Shipment(
        # ...
        cargo_description=_cargo_summary_from_so(so),
        weight=getattr(so, "weight", None),
        volume=getattr(so, "volume", None),
        qty=getattr(so, "qty", None),
        # ...
    )


