from decimal import Decimal
from django.db.models import Sum

def _tax_rate_percent(tax) -> Decimal:
    """
    Ambil rate dari core.Tax.
    Default pakai 'rate'. Kalau model Tax kamu pakai nama lain,
    ganti di sini (mis: percent).
    """
    return Decimal(getattr(tax, "rate", 0) or 0)


def compute_line_tax_amount(line) -> Decimal:
    """
    Pajak dihitung dari line.amount berdasarkan taxes M2M.
    """
    base = Decimal(line.amount or 0)
    total = Decimal("0")

    taxes = getattr(line, "taxes", None)
    if taxes is None:
        return Decimal("0.00")

    for t in taxes.all():
        rate = _tax_rate_percent(t) / Decimal("100")
        total += (base * rate)

    return total.quantize(Decimal("0.01"))


def recompute_vendor_booking_totals(vb):
    """
    subtotal = sum(lines.amount)
    tax_total = sum(line taxes)
    wht_amount = subtotal * wht_rate%
    total_amount = subtotal + tax_total - wht_amount

    Catatan: currency + idr_rate sudah di header, jadi tidak dihitung di sini.
    """
    subtotal = vb.lines.aggregate(s=Sum("amount"))["s"] or Decimal("0")

    tax_total = Decimal("0")
    for ln in vb.lines.all().prefetch_related("taxes"):
        tax_total += compute_line_tax_amount(ln)
    tax_total = tax_total.quantize(Decimal("0.01"))

    wht_rate = Decimal(getattr(vb, "wht_rate", 0) or 0) / Decimal("100")
    wht_amount = (subtotal * wht_rate).quantize(Decimal("0.01"))

    # Set header fields
    vb.wht_amount = wht_amount
    vb.total_amount = (subtotal + tax_total - wht_amount).quantize(Decimal("0.01"))

    # kalau kamu punya field subtotal/tax_total di header, boleh update juga di sini
    update_fields = ["wht_amount", "total_amount"]
    vb.save(update_fields=update_fields)

    return {
        "subtotal": subtotal.quantize(Decimal("0.01")),
        "tax_total": tax_total,
        "wht_amount": wht_amount,
        "total_amount": vb.total_amount,
    }
