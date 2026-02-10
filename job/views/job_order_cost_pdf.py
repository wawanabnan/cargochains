import os
import pdfkit
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from job.models.job_orders import JobOrder



def build_context_for_print(job):
    """
    COPY dari view print preview kamu.
    Ini versi minimal yang match template terakhir kamu.
    """
    from decimal import Decimal, ROUND_HALF_UP

    def q2(x):
        return Decimal(x or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    job_ccy = (job.currency.code or "IDR").upper()
    job_rate = q2(job.kurs_idr if job_ccy != "IDR" else 1)

    job_value = q2(job.total_amount)
    if job_ccy == "IDR":
        job_value_idr = job_value
    else:
        job_value_idr = q2(job.total_in_idr) if q2(job.total_in_idr) > 0 else q2(job_value * job_rate)

    costs = job.job_costs.all().select_related("cost_type", "vendor", "currency")

    lines = []
    total_cost_idr = Decimal("0")

    for c in costs:
        amount_idr = q2(getattr(c, "est_amount", 0) or 0)
        total_cost_idr += amount_idr

        # template kamu pakai ln.price → pastikan ada field price di JobCost
        price = q2(getattr(c, "price", 0) or 0)
        rate = q2(getattr(c, "rate", 1) or 1)

        line_ccy = (c.currency.code if getattr(c, "currency_id", None) else job_ccy).upper()

        lines.append({
            "cost_type": getattr(c.cost_type, "name", str(c.cost_type)),
            "vendor": str(c.vendor) if getattr(c, "vendor_id", None) else "",
            "qty": c.qty,
            "currency": line_ccy,
            "price": price,
            "rate": rate,
            "amount_idr": amount_idr,
        })

    profit_idr = q2(job_value_idr - total_cost_idr)

    return {
        "job": job,
        "job_ccy": job_ccy,
        "job_rate": job_rate,
        "job_value": job_value,
        "job_value_idr": job_value_idr,
        "lines": lines,
        "total_cost_idr": q2(total_cost_idr),
        "profit_idr": profit_idr,

        # template kamu masih pakai base_code/is_idr di beberapa tempat (meski dikomentari)
        "base_code": job_ccy,
        "is_idr": (job_ccy == "IDR"),
    }



from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

from weasyprint import HTML


@login_required
def joborder_cost_pdf(request, pk):
    # ctx kamu sudah punya dari logic sebelumnya
    # contoh:
    # job = get_object_or_404(JobOrder, pk=pk)
    # ctx = build_context_for_print(job)

    ctx = ...  # <-- pakai ctx yang sama dengan preview

    html = render_to_string(
        "job_order/print_cost_preview.html",
        ctx,
        request=request
    )

    # penting supaya {% static %}, img, css kebaca
    base_url = request.build_absolute_uri("/")

    # WeasyPrint otomatis:
    # - include background
    # - hormati @page di CSS
    pdf_bytes = HTML(
        string=html,
        base_url=base_url
    ).write_pdf()

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="job-cost.pdf"'
    return resp
