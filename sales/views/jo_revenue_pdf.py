# sales/views/jo_revenue_pdf.py

from decimal import Decimal
import os
import tempfile

import pdfkit
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views import View

from sales.job_order_model import JobOrder,JobCost


class JobOrderRevenuePdfView(LoginRequiredMixin, View):
    template_name = "job_orders/jo_pdf.html"

    def get(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)

        # ---------- 1) REVENUE IDR ----------
        # Kalau om sudah simpan total_in_idr di model, pakai itu:
        revenue_idr = job.total_in_idr or Decimal("0.00")

        # (fallback kalau belum ada total_in_idr, pakai grand_total saja)
        if not revenue_idr:
            revenue_idr = job.grand_total or Decimal("0.00")

        # ---------- 2) COGS: JOB COST (IDR) ----------
        costs_qs = JobCost.objects.filter(job_order=job)

        items_cost_idr = (
            costs_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )

        # ---------- 3) TAX (IDR) ----------
        # Tax di header job order anggap sudah 1.1% dari revenue, simpan di IDR.
        # Kalau tax_amount masih di currency asing, om bisa kalikan kurs di sini.
        # Di contoh om, tax adalah 2.145.000,00.
        tax_idr = getattr(job, "tax_idr", None)
        if tax_idr is None:
            # fallback: hitung dari revenue_idr * 1.1% jika is_tax True
            if getattr(job, "is_tax", False):
                tax_idr = (revenue_idr * Decimal("0.011")).quantize(Decimal("0.01"))
            else:
                tax_idr = Decimal("0.00")

        # ---------- 4) TOTAL COGS & PROFIT (IDR) ----------
        total_cogs_idr = (items_cost_idr + tax_idr).quantize(Decimal("0.01"))
        gross_profit_idr = (revenue_idr - total_cogs_idr).quantize(Decimal("0.01"))

        # ---------- 5) HEADER & FOOTER (wkhtmltopdf) ----------
        header_url = request.build_absolute_uri(static("img/letter_header_bg.png"))
        footer_url = request.build_absolute_uri(static("img/letter_footer_bg.png"))

        header_html = render_to_string("sales/pdf/header.html", {"header_url": header_url})
        footer_html = render_to_string("sales/pdf/footer.html", {"footer_url": footer_url})

        tmp_header = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp_footer = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp_header.write(header_html.encode("utf-8"))
        tmp_footer.write(footer_html.encode("utf-8"))
        tmp_header.close()
        tmp_footer.close()

        # ---------- 6) BODY HTML ----------
        html = render_to_string(
            self.template_name,
            {
                "job": job,
                "currency_code": job.currency.code,
                "kurs": job.kurs_idr or Decimal("1.00"),

                "costs": costs_qs,
                "items_cost_idr": items_cost_idr,
                "tax_idr": tax_idr,
                "total_cogs_idr": total_cogs_idr,
                "revenue_idr": revenue_idr,
                "gross_profit_idr": gross_profit_idr,
                "is_pdf": True,
            },
        )

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

        pdf_content = pdfkit.from_string(html, False, options=options, configuration=config)

        os.unlink(tmp_header.name)
        os.unlink(tmp_footer.name)

        filename = f"Revenue-{job.number}.pdf"
        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
