from decimal import Decimal, ROUND_HALF_UP

Q2 = Decimal("0.01")

def q2(x: Decimal) -> Decimal:
    return (x or Decimal("0")).quantize(Q2, rounding=ROUND_HALF_UP)

def calc_line_amount(qty, unit_price) -> Decimal:
    qty = Decimal(str(qty or "0"))
    unit_price = Decimal(str(unit_price or "0"))
    return q2(qty * unit_price)

def calc_booking_totals(vb) -> dict:
    """
    Expected:
      vb.lines related_name='lines' (or adjust)
      vb.discount_amount, vb.wht_rate
      line.amount already stored, taxes M2M with 'rate' in percent
    """
    subtotal = Decimal("0")
    tax_amount = Decimal("0")

    lines_qs = vb.lines.all()
    for ln in lines_qs:
        subtotal += Decimal(str(ln.amount or "0"))

        # taxes: each tax has .rate (percent)
        for tx in ln.taxes.all():
            rate = Decimal(str(getattr(tx, "rate", 0) or "0")) / Decimal("100")
            tax_amount += (Decimal(str(ln.amount or "0")) * rate)

    subtotal = q2(subtotal)
    tax_amount = q2(tax_amount)

    discount = q2(Decimal(str(vb.discount_amount or "0")))
    taxable_base = q2(subtotal - discount)

    wht_rate = Decimal(str(vb.wht_rate or "0")) / Decimal("100")
    wht_amount = q2(taxable_base * wht_rate)

    total = q2(taxable_base + tax_amount - wht_amount)

    return {
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "discount_amount": discount,
        "wht_amount": wht_amount,
        "total_amount": total,
    }
