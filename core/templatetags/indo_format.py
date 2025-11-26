# core/templatetags/indo_format.py
from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


def _to_decimal(value):
    """
    Helper: konversi ke Decimal dengan aman.
    Kalau gagal, balikin apa adanya.
    """
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


@register.filter
def indo_number(value, decimal_places=2):
    """
    Format angka gaya Indonesia:
    - ribuan = titik
    - desimal = koma

    Contoh:
      {{ 1500000.75|indo_number }}      → 1.500.000,75
      {{ 1500000|indo_number:0 }}       → 1.500.000
    """
    dec = _to_decimal(value)
    if dec is None:
        return value

    # format standard: 1,500,000.75
    fmt = f"{dec:,.{int(decimal_places)}f}"

    # tukar koma & titik
    fmt = fmt.replace(",", "X").replace(".", ",").replace("X", ".")
    return fmt


@register.filter
def indo_currency(value, currency_code=""):
    """
    Format angka + kode mata uang.
    Contoh:
      {{ fq.total_amount|indo_currency:fq.currency.code }}
    """
    dec = _to_decimal(value)
    if dec is None:
        return value

    fmt = indo_number(dec, 2)
    code = (currency_code or "").strip()
    return f"{fmt} {code}" if code else fmt
