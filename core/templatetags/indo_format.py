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




# ============================================================
#  TERBILANG (angka → teks bahasa Indonesia)
# ============================================================

ONES = [
    "", "satu", "dua", "tiga", "empat", "lima",
    "enam", "tujuh", "delapan", "sembilan"
]

THOUSANDS = [
    "", "ribu", "juta", "miliar", "triliun"
]


def _terbilang_integer(n):
    """Konversi bilangan bulat ke terbilang."""
    n = int(n)
    if n == 0:
        return "nol"

    words = []
    group = 0

    while n > 0:
        num = n % 1000
        if num != 0:
            words.append(_spell_group(num, THOUSANDS[group]))
        n //= 1000
        group += 1

    return " ".join(reversed(words)).strip()


def _spell_group(n, suffix):
    """Terbilang 0–999."""
    words = []

    hundreds = n // 100
    tens_units = n % 100
    tens = tens_units // 10
    ones = tens_units % 10

    # ratus
    if hundreds > 0:
        if hundreds == 1:
            words.append("seratus")
        else:
            words.append(ONES[hundreds] + " ratus")

    # puluh / belas / satuan
    if tens_units > 0:
        if tens_units < 10:
            words.append(ONES[tens_units])
        elif tens_units < 20:
            if tens_units == 10:
                words.append("sepuluh")
            elif tens_units == 11:
                words.append("sebelas")
            else:
                words.append(ONES[ones] + " belas")
        else:
            words.append(ONES[tens] + " puluh")
            if ones > 0:
                words.append(ONES[ones])

    if suffix:
        words.append(suffix)

    return " ".join(words)


@register.filter
def indo_terbilang(value):
    """
    Ubah angka menjadi teks terbilang bahasa Indonesia.
    Contoh:
      {{ 1500000|indo_terbilang }}
      → 'satu juta lima ratus ribu'

      {{ 1500000.75|indo_terbilang }}
      → 'satu juta lima ratus ribu koma tujuh lima'
    """
    try:
        value = str(value).replace(",", ".")     # normalisasi
        if "." in value:
            whole, frac = value.split(".")
            whole_words = _terbilang_integer(int(whole))
            frac_words = " ".join(ONES[int(d)] for d in frac if d.isdigit())
            return f"{whole_words} koma {frac_words}".strip()
        else:
            return _terbilang_integer(int(value))
    except:
        return value
