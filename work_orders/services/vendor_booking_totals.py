from decimal import Decimal
from django.db.models import Sum


def _d(v, default="0") -> Decimal:
    """Safe Decimal coercion."""
    if v is None or v == "":
        return Decimal(default)
    try:
        return Decimal(v)
    except Exception:
        return Decimal(default)


def _tax_rate_percent(tax) -> Decimal:
    """
    Ambil rate dari core.Tax.
    Default pakai 'rate'. Kalau model Tax kamu pakai nama lain,
    ganti di sini (mis: percent).
    """
    return _d(getattr(tax, "rate", 0) or 0)


def compute_line_tax_amount(line) -> Decimal:
    """
    Pajak dihitung dari line.amount berdasarkan taxes M2M.
    """
    base = _d(getattr(line, "amount", 0) or 0)
    total = Decimal("0")

    taxes = getattr(line, "taxes", None)
    if taxes is None:
        return Decimal("0.00")

    for t in taxes.all():
        rate = _tax_rate_percent(t) / Decimal("100")
        total += (base * rate)

    return total.quantize(Decimal("0.01"))


def recompute_line_amounts(vb) -> None:
    """
    Defensive: pastikan line.amount konsisten dengan qty * unit_price.
    Panggil ini sebelum aggregate subtotal jika kamu tidak 100% yakin
    amount selalu dihitung di UpdateView.
    """
    for ln in vb.lines.all():
        qty = _d(getattr(ln, "qty", 0) or 0)
        unit_price = _d(getattr(ln, "unit_price", 0) or 0)
        amount = (qty * unit_price).quantize(Decimal("0.01"))

        current = _d(getattr(ln, "amount", 0) or 0).quantize(Decimal("0.01"))
        if current != amount:
            ln.amount = amount
            ln.save(update_fields=["amount"])


def recompute_vendor_booking_totals(vb, *, recompute_lines: bool = False):
    """
    subtotal = sum(lines.amount)
    tax_total = sum(line taxes)
    wht_amount = subtotal * wht_rate%
    total_amount = subtotal - discount + tax_total - wht_amount

    Catatan: currency + idr_rate sudah di header, jadi tidak dihitung di sini.
    """
    if recompute_lines:
        recompute_line_amounts(vb)

    subtotal = _d(vb.lines.aggregate(s=Sum("amount"))["s"] or 0).quantize(Decimal("0.01"))

    tax_total = Decimal("0")
    for ln in vb.lines.all().prefetch_related("taxes"):
        tax_total += compute_line_tax_amount(ln)
    tax_total = tax_total.quantize(Decimal("0.01"))

    discount = _d(getattr(vb, "discount_amount", 0) or 0).quantize(Decimal("0.01"))

    wht_rate = _d(getattr(vb, "wht_rate", 0) or 0) / Decimal("100")
    wht_amount = (subtotal * wht_rate).quantize(Decimal("0.01"))

    total_amount = (subtotal - discount + tax_total - wht_amount).quantize(Decimal("0.01"))

    # Set header fields (update kalau field exist)
    vb.subtotal_amount = subtotal
    vb.tax_amount = tax_total
    vb.wht_amount = wht_amount
    vb.total_amount = total_amount

    update_fields = ["subtotal_amount", "tax_amount", "wht_amount", "total_amount"]
    # discount_amount ada/akan ada, tapi tidak wajib di-update di sini
    if hasattr(vb, "discount_amount"):
        # value sudah ada di vb, tapi kalau mau konsisten di update_fields:
        if "discount_amount" not in update_fields:
            # optional: kalau kamu mau selalu include
            pass

    vb.save(update_fields=update_fields)

    return {
        "subtotal": subtotal,
        "tax_total": tax_total,
        "discount_amount": discount,
        "wht_amount": wht_amount,
        "total_amount": total_amount,
    }
