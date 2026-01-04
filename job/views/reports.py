from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

import os
import subprocess
import tempfile

from job.models.job_orders import JobOrder  # ✅ sesuaikan path model


def _get_sales_report_qs(request):
    qs = JobOrder.objects.all().select_related("customer")

    date_from = request.GET.get("from") or ""
    date_to = request.GET.get("to") or ""
    customer_id = request.GET.get("customer") or ""
    status = request.GET.get("status") or ""

    if date_from:
        qs = qs.filter(job_date__gte=date_from)
    if date_to:
        qs = qs.filter(job_date__lte=date_to)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    if status:
        qs = qs.filter(status=status)

    return qs


@login_required
def sales_report(request):
    qs = _get_sales_report_qs(request)

    # ✅ Revenue source dari JobOrder (ganti field sesuai model om)
    total_revenue = qs.aggregate(total=Sum("grand_total"))["total"] or Decimal("0")

    ctx = {
        "rows": qs.order_by("-job_date", "-id")[:2000],
        "total_revenue": total_revenue,
        "printed_at": timezone.now(),
    }
    return render(request, "reports/sales_report.html", ctx)


def _wkhtmltopdf_bytes(html: str, *, page_size="A4", orientation="Portrait"):
    """
    Render HTML -> PDF via wkhtmltopdf CLI.
    Windows-friendly, tidak butuh library tambahan.
    """
    wkhtml = getattr(settings, "WKHTMLTOPDF_CMD", "wkhtmltopdf")

    with tempfile.TemporaryDirectory() as td:
        html_path = os.path.join(td, "in.html")
        pdf_path = os.path.join(td, "out.pdf")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        cmd = [
            wkhtml,
            "--quiet",
            "--page-size", page_size,
            "--orientation", orientation,
            "--margin-top", "10",
            "--margin-right", "10",
            "--margin-bottom", "10",
            "--margin-left", "10",
            "--encoding", "utf-8",
            html_path,
            pdf_path,
        ]

        subprocess.check_call(cmd)

        with open(pdf_path, "rb") as f:
            return f.read()


@login_required
def sales_report_pdf(request):
    qs = _get_sales_report_qs(request)
    total_revenue = qs.aggregate(total=Sum("grand_total"))["total"] or Decimal("0")

    html = render_to_string(
        "reports/sales_report_pdf.html",
        {
            "rows": qs.order_by("-job_date", "-id")[:5000],
            "total_revenue": total_revenue,
            "printed_at": timezone.now(),
            "request": request,
        },
    )

    pdf_bytes = _wkhtmltopdf_bytes(html)

    filename = "sales-report.pdf"
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp
