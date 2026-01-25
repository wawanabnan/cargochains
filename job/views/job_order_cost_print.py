from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from job.models.job_orders import JobOrder

def q2(x) -> Decimal:
    return Decimal(x or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

@login_required
def joborder_cost_print_preview(request, pk):
    job = get_object_or_404(
        JobOrder.objects.select_related("currency", "customer", "service", "payment_term"),
        pk=pk
    )

    job_ccy = (job.currency.code or "IDR").upper()
    job_rate = q2(job.kurs_idr if job_ccy != "IDR" else 1)
    
    
    job_value = q2(job.total_amount)  # ✅ ada di model kamu
    if job_ccy == "IDR":
        job_value_idr = job_value
    else:
        job_value_idr = q2(job.total_in_idr) if q2(job.total_in_idr) > 0 else q2(job_value * job_rate)

    costs = job.job_costs.all().select_related("cost_type", "uom", "vendor", "currency")

    lines = []
    total_cost_amount_idr = Decimal("0")  # no tax
    total_cost_tax_idr = Decimal("0")
    total_cost_idr = Decimal("0")
    
    for c in costs:
        amount_idr = q2(getattr(c, "est_amount", 0) or 0)   # ✅ sudah hasil konversi (IDR)
        tax_idr = q2(getattr(c, "tax", 0) or 0)
        line_total_idr = amount_idr + tax_idr

        total_cost_amount_idr += amount_idr
        total_cost_tax_idr += tax_idr
        total_cost_idr += line_total_idr

        line_ccy = (c.currency.code if getattr(c, "currency_id", None) else job_ccy).upper()
        line_rate = q2(getattr(c, "rate", 1) or 1)

        lines.append({
            "cost_type": getattr(c.cost_type, "name", str(c.cost_type)),
            "description": c.description or "",
            "qty": c.qty,
            "uom": getattr(c.uom, "code", "") if getattr(c, "uom_id", None) else "",
            "vendor": str(c.vendor) if getattr(c, "vendor_id", None) else "",
            "currency": line_ccy,
            "price": c.price,
            "rate": line_rate,
            "amount_idr": amount_idr,
            "tax_idr": tax_idr,
            "total_idr": line_total_idr,
        })

    profit_idr = q2(job_value_idr - total_cost_amount_idr)

    return render(request, "job_order/print_cost_preview.html", {
        "job": job,

        # Header amounts
        "job_ccy": job_ccy,
        "job_rate": job_rate,
        "job_value": job_value,
        "job_value_idr": job_value_idr,

        # Lines + totals
        "lines": lines,
        "total_cost_amount_idr": q2(total_cost_amount_idr),
        "total_cost_tax_idr": q2(total_cost_tax_idr),
        "total_cost_idr": q2(total_cost_idr),

        # Profitability
        "profit_idr": profit_idr,
    })
