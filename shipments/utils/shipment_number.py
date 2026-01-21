# shipments/utils.py
from datetime import date
from django.utils import timezone

try:
    # kamu sudah pakai ini di sales quotation kemarin
    from core.utils import get_next_number
except Exception:
    get_next_number = None  # fallback di bawah

from shipments.models.shipments import Shipment


def next_shipment_number(for_date: date | None = None) -> str:
    """
    Format: S-mmyy-0001
    Reset setiap bulan (mmyy berbeda → counter balik ke 0001).
    Menggunakan core.utils.get_next_number jika tersedia; jika tidak, fallback aman dengan query.
    """
    d = for_date or timezone.localdate()
    prefix = f"S-{d.strftime('%m%y')}-"

    # --- Pakai core.utils jika tersedia ---
    if get_next_number:
        # Pola yang umum kita pakai: namespace + key berbasis bulan
        # Misal di CoreSetting/sequence kamu simpan per kunci "SHIPMENT_YYYYMM"
        scope_key = f"SHIPMENT_{d.strftime('%Y%m')}"
        # Beberapa implementasi get_next_number hanya butuh (app, key)
        # lalu kamu yang format. Jadi kita coba ambil next int, lalu format ke 4 digit.
        try:
            seq_raw = get_next_number("shipments", scope_key)  # ekspektasi: mengembalikan integer/angka string
            try:
                seq_int = int(str(seq_raw))
            except ValueError:
                # kalau ternyata sudah kasih string final, langsung return
                if str(seq_raw).startswith(prefix):
                    return str(seq_raw)
                # kalau bukan, kita jatuhkan ke fallback
                raise
            return f"{prefix}{seq_int:04d}"
        except Exception:
            # jatuh ke fallback kalau signature beda
            pass

    # --- Fallback aman (tanpa core.utils) ---
    # Cari nomor terakhir dengan prefix bulan berjalan, ambil 4 digit terakhir, +1
    last = (
        Shipment.objects
        .filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    if not last:
        return f"{prefix}0001"
    # Ekstrak urutan 4 digit
    tail = last.rsplit("-", 1)[-1]
    try:
        nxt = int(tail) + 1
    except Exception:
        nxt = 1
    return f"{prefix}{nxt:04d}"
