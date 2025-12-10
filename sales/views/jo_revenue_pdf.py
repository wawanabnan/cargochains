# sales/views/jo_revenue_pdf.py

import os
import tempfile
import pdfkit

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views import View

from sales.job_order_model import JobOrder


class JobOrderRevenuePdfView(LoginRequiredMixin, View):
    """
    Revenue PDF:
    - Revenue = job.grand_total
    - COGS = total JobCost + Tax (header)
    - Gross Profit = Revenue - COGS
    Menggunakan header/footer seperti FO.
    """

    template_name = "job_orders/jo_pdf.html"

    def get(self, request, pk):

        # ==============================
        # 1) AMBIL DATA JOB & COSTS
        # ==============================
        job = get_object_or_404(JobOrder, pk=pk)

        # related_name harus sesuai (job.costs / job.job_costs)
        costs = job.costs.all().order_by("id")

        items_cost = sum((c.amount for c in costs), 0)
        tax_cost = job.tax_amount or 0
        total_cogs = items_cost + tax_cost

        revenue = job.grand_total or 0
        gross_profit = revenue - total_cogs

        # ==============================
        # 2) HEADER & FOOTER HTML
        # ==============================
        header_url = request.build_absolute_uri(static("img/letter_header_bg.png"))
        footer_url = request.build_absolute_uri(static("img/letter_footer_bg.png"))

        header_html = render_to_string("sales/pdf/header.html", {
            "header_url": header_url,
        })
        footer_html = render_to_string("sales/pdf/footer.html", {
            "footer_url": footer_url,
        })

        tmp_header = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp_footer = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp_header.write(header_html.encode("utf-8"))
        tmp_footer.write(footer_html.encode("utf-8"))
        tmp_header.close()
        tmp_footer.close()

        # ==============================
        # 3) BODY HTML
        # ==============================
        html = render_to_string(self.template_name, {
            "job": job,
            "costs": costs,
            "items_cost": items_cost,
            "tax_cost": tax_cost,
            "total_cogs": total_cogs,
            "revenue": revenue,
            "gross_profit": gross_profit,
            "is_pdf": True,
        })

        # ==============================
        # 4) WKHTMLTOPDF OPTIONS
        # ==============================
        options = {
            "page-size": "A4",
            "encoding": "UTF-8",
            "margin-top": "30mm",
            "margin-bottom": "45mm",
            "margin-left": "0mm",
            "margin-right": "0mm",
            "header-html": tmp_header.name,
            "footer-html": tmp_footer.name,
            "header-spacing": "0",
            "footer-spacing": "0",
            "enable-local-file-access": None,
        }

        wkhtml_path = getattr(settings, "WKHTMLTOPDF_CMD", None)
        config = pdfkit.configuration(wkhtmltopdf=wkhtml_path) if wkhtml_path else None

        pdf_content = pdfkit.from_string(
            html,
            False,
            options=options,
            configuration=config,
        )

        # hapus tmp file
        os.unlink(tmp_header.name)
        os.unlink(tmp_footer.name)

        filename = f"Revenue-{job.number}.pdf"
        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
