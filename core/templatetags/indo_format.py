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


@register.filter
def indo_terbilang_uang(value):
    """
    Terbilang untuk nominal uang:
    - Jika desimal 00 -> tambah "saja" (tanpa "koma")
    - Jika desimal != 00 -> "koma ..." (lebih natural)

    Contoh:
      30330000.00 -> "tiga puluh juta tiga ratus tiga puluh ribu saja"
      1250.50     -> "seribu dua ratus lima puluh koma lima puluh"
      100.05      -> "seratus koma nol lima"
    """
    try:
        s = str(value).strip()

        # normalisasi format indo: 30.330.000,00 -> 30330000.00
        s = s.replace(" ", "")
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        else:
            # kalau format sudah 1000.00 (dot decimal), biarkan
            pass

        if "." in s:
            whole_str, frac_str = s.split(".", 1)
        else:
            whole_str, frac_str = s, ""

        whole = int(whole_str) if whole_str not in ("", None) else 0
        whole_words = _terbilang_integer(whole).strip()

        # ambil 2 digit pecahan (uang)
        frac2 = (frac_str + "00")[:2]
    
        if frac2 == "00":
            return f"{whole_words} rupiah saja".strip() 
        # jika pecahan leading zero, bacakan per digit biar "nol lima"
        if frac2[0] == "0" and frac2[1] != "0":
            frac_words = f"nol {ONES[int(frac2[1])]}"
        else:
            frac_words = _terbilang_integer(int(frac2)).strip()

        return f"{whole_words} rupiah koma {frac_words}".strip()

    except Exception:
        return value
