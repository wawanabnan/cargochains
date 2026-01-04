from decimal import Decimal
from core.models.exchange_rates import ExchangeRate

def get_rate_to_idr(currency, on_date):
    """
    Ambil rate_to_idr terbaru dengan rate_date <= on_date.
    Return Decimal atau None.
    """
    if not currency:
        return None

    code = (getattr(currency, "code", "") or "").upper()
    if code == "IDR":
        return Decimal("1.0")

    return (
        ExchangeRate.objects
        .filter(currency=currency, is_active=True, rate_date__lte=on_date)
        .order_by("-rate_date")
        .values_list("rate_to_idr", flat=True)
        .first()
    )
