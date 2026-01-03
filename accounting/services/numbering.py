from datetime import date
from django.db import transaction

from core.models.number_sequences import NumberSequence   # ⬅️ INI representasi core_numbering_sequence


def _format_period(dt: date, fmt: str) -> str:
    if fmt == "YYYY":
        return dt.strftime("%Y")
    if fmt == "YYYYMM":
        return dt.strftime("%Y%m")
    raise ValueError(f"Invalid period_format: {fmt}")


from datetime import date
from core.utils.numbering  import get_next_number


def next_journal_number(journal_date: date, kind: str = "GJ") -> str:
    """
    Generate journal number using core.utils.get_next_number()
    - kind OPEN -> code JOURNAL_OPEN
    - else      -> code JOURNAL_JV (JV/GJ/etc)
    """
    kind = (kind or "GJ").upper()
    code = "JOURNAL_OPEN" if kind == "OPEN" else "JOURNAL_JV"

    # app_label sesuaikan dengan NumberSequence om.
    # Kalau semua sequence om pakai app_label="accounting" utk journal, pakai ini:
    return get_next_number("accounting", code, today=journal_date)
