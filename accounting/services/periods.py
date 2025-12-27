from datetime import date
from accounting.models.period_lock import AccountingPeriodLock
from accounting.models.settings import AccountingSettings


def get_active_fiscal_year() -> int:
    return AccountingSettings.get_active_year()


def is_period_locked(d: date) -> bool:
    """
    Return True jika periode terkunci.
    Policy:
    - OPEN_IF_MISSING: jika record period lock tidak ada => dianggap OPEN (False)
    - STRICT_REQUIRE : jika record period lock tidak ada => dianggap BLOCK (True)
    """
    qs = AccountingPeriodLock.objects.filter(year=d.year, month=d.month)
    if not qs.exists():
        return AccountingSettings.get_posting_policy() == AccountingSettings.PostingPolicy.STRICT_REQUIRE
    return qs.filter(is_locked=True).exists()
