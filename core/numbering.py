# core/numbering.py
from datetime import date
from django.db import transaction

def format_period(year: int, month: int, fmt: str) -> str:
    if fmt == "YYYY":
        return f"{year:04d}"
    if fmt == "YYYYMM":
        return f"{year:04d}{month:02d}"
    if fmt == "MMYY":
        return f"{month:02d}{str(year)[-2:]}"
    return ""  # NONE

@transaction.atomic
def next_number(seq_qs, *, today: date | None = None) -> str:
    """
    seq_qs = queryset NumberSequence yg sudah difilter (mis. by app_label, code, branch, mode)
    - Mengunci row pakai select_for_update
    - Reset counter saat ganti periode sesuai period_format
    - Return nomor lengkap: prefix + period + counter(zfill)
    """
    from .models import NumberSequence  # import lokal biar aman saat app layout berubah
    if today is None:
        today = date.today()

    seq = (seq_qs.select_for_update()
                 .filter(active=True)
                 .get())  # pastikan hanya satu row utk kombinasi itu

    # reset kalau period_format bukan NONE dan bulan/tahun berubah
    needs_period = seq.period_format in ("YYYY", "YYYYMM", "MMYY")
    if needs_period:
        if (seq.period_year, seq.period_month) != (today.year, today.month):
            seq.period_year, seq.period_month, seq.last_no = today.year, today.month, 0

    seq.last_no += 1
    seq.save(update_fields=["period_year", "period_month", "last_no"])

    period = format_period(seq.period_year, seq.period_month, seq.period_format) if needs_period else ""
    counter = str(seq.last_no).zfill(seq.padding)
    return f"{seq.prefix}{period}{counter}"
