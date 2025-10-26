# core/utils.py
from datetime import date
from django.db import transaction
from django.utils import timezone
from core.models import NumberSequence

def get_next_number(app_label: str, code: str, today: date | None = None) -> str:
    """
    Ambil/buat sequence lalu naikkan counter secara atomic dan kembalikan nomor terformat.
    Mendukung token format:
      {prefix} {year} {yy} {month} {day} {seq}
    Contoh format di DB: "{prefix}-{month:02d}{yy:02d}-{seq:04d}"
    """
    today = today or timezone.localdate()
    year, month, day = today.year, today.month, today.day
    yy = year % 100  # dua digit tahun

    with transaction.atomic():
        seq, _ = NumberSequence.objects.select_for_update().get_or_create(
            app_label=app_label,
            code=code,
            defaults={
                "name": f"{app_label}/{code}",
                "prefix": "",
                "format": "{prefix}-{month:02d}{yy:02d}-{seq:04d}",
                "reset": "monthly",          # atau "yearly"/"none" sesuai kebijakanmu
                "last_number": 0,
                "period_year": year,
                "period_month": month,
                "padding": 4,
            },
        )

        # reset counter saat periode berubah
        if getattr(seq, "reset", "monthly") == "yearly":
            if (seq.period_year or 0) != year:
                seq.last_number = 0
                seq.period_year, seq.period_month = year, month
        elif getattr(seq, "reset", "monthly") == "monthly":
            if (seq.period_year or 0) != year or (seq.period_month or 0) != month:
                seq.last_number = 0
                seq.period_year, seq.period_month = year, month
        # "none" → tidak reset

        # naikkan counter
        seq.last_number = (seq.last_number or 0) + 1
        seq.save(update_fields=["last_number", "period_year", "period_month"])

        # render output dari format di DB
        fmt = getattr(seq, "format", None) or "{prefix}-{month:02d}{yy:02d}-{seq:04d}"

        # Jika admin lupa kasih {:0Nd} di {seq}, hormati padding secara manual
        if "{seq:" not in fmt:
            seq_str = str(seq.last_number).zfill(seq.padding or 0)
            return fmt.format(prefix=seq.prefix or "", year=year, yy=yy, month=month, day=day, seq=seq_str)

        return fmt.format(prefix=seq.prefix or "", year=year, yy=yy, month=month, day=day, seq=seq.last_number)
