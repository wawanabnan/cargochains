# views.py
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from playwright.sync_api import sync_playwright

from job.models.job_orders import JobOrder


def joborder_cost_pdf(request, pk):
    job = get_object_or_404(
        JobOrder.objects.select_related("currency", "customer"),
        pk=pk
    )

    # ===== Ambil context yang sama dengan preview =====
    ctx = build_context_for_print(job)

    ctx["watermark_status"] = job.status.upper()   # contoh: DRAFT / APPROVED

    # Bisa reuse template preview (atau ganti ke print_cost_pdf.html kalau kamu bikin khusus)
    html = render_to_string("job_order/print_cost_pdf.html", ctx, request=request)

    base_url = request.build_absolute_uri("/")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            # kalau jalan di docker/linux kadang perlu:
            # args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = browser.new_page()

        page.set_content(html, wait_until="networkidle")

        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True,  # hormati @page di base template
            # margin nggak perlu kalau sudah pakai @page margin
            # margin={"top":"12mm","right":"12mm","bottom":"14mm","left":"12mm"},
        )

        browser.close()

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="job-cost-{job.number}.pdf"'
    return resp


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
        "base_code": job_ccy,
        "is_idr": (job_ccy == "IDR"),
    }
