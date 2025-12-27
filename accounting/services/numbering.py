from datetime import date
from django.db import transaction

from core.models.number_sequences import NumberSequence   # ⬅️ INI representasi core_numbering_sequence


def _format_period(dt: date, fmt: str) -> str:
    if fmt == "YYYY":
        return dt.strftime("%Y")
    if fmt == "YYYYMM":
        return dt.strftime("%Y%m")
    raise ValueError(f"Invalid period_format: {fmt}")


def next_journal_number(journal_date: date, kind: str = "GJ") -> str:
    """
    Generate journal number using core_numbering_sequence

    OPEN -> OPEN-YYYY-0001
    GJ   -> JV-YYYYMM-0001
    """
    kind = (kind or "GJ").upper()

    if kind == "OPEN":
        seq_code = "JOURNAL_OPEN"
    else:
        seq_code = "JOURNAL_JV"

    with transaction.atomic():
        seq = (
            NumberSequence.objects
            .select_for_update()
            .get(code=seq_code, is_active=True)
        )

        period = _format_period(journal_date, seq.period_format)
        number = f"{seq.prefix}-{period}-{str(seq.next_number).zfill(seq.padding)}"

        seq.next_number += 1
        seq.save(update_fields=["next_number"])

    return number
