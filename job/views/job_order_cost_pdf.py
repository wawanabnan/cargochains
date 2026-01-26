import os
import pdfkit
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from job.models.job_orders import JobOrder


def joborder_cost_pdf_wkhtml(request, pk):
    job = get_object_or_404(
        JobOrder.objects.select_related("currency", "customer"),
        pk=pk
    )

    # ===== Ambil data yang sama seperti preview =====
    # PENTING: context ini HARUS sama dengan preview supaya template tidak kosong.
    # Aku asumsi kamu sudah punya view preview yang bikin context ini.
    # Jadi: copy konteks dari view preview kamu dan pakai di sini.
    ctx = build_context_for_print(job)  # <- lihat fungsi di bawah

    html = render_to_string("job_order/print_cost_pdf.html", ctx, request=request)

    # ===== wkhtmltopdf config =====
    wkhtml_path = getattr(settings, "WKHTMLTOPDF_CMD", None)
    if wkhtml_path:
        config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)
    else:
        config = None  # pakai default dari PATH

    options = {
        "page-size": "A4",
        "margin-top": "12mm",
        "margin-right": "12mm",
        "margin-bottom": "14mm",
        "margin-left": "12mm",
        "encoding": "UTF-8",
        "print-media-type": "",          # pakai CSS @media print
        "enable-local-file-access": "",  # penting kalau ada static/local assets
        # "disable-smart-shrinking": "",  # aktifkan kalau layout suka mengecil sendiri
    }

    pdf = pdfkit.from_string(html, False, options=options, configuration=config)

    resp = HttpResponse(pdf, content_type="application/pdf")
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
