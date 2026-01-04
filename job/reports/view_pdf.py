# job/reports/views_pdf.py

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


from job.models.job_orders import JobOrder
from job.models.costs import JobCost


D0 = Decimal("0.00")
D1 = Decimal("1.00")


class JobProfitabilityPdfView(LoginRequiredMixin, View):
    """
    Sales Profitability PDF (per Job):
    - Revenue (IDR) dari job.total_amount (+ kurs)
    - COGS detail dari JobCost.est_amount (bukan journal)
    - PDF pakai pdfkit + header/footer (pola CargoChains)
    """
    template_name = "reports/pdf/job_profitability_pdf.html"

    def get(self, request, job_id: int):
        job = get_object_or_404(JobOrder, pk=job_id)

        # ==========================
        # BASE DATA
        # ==========================
        currency_code = getattr(getattr(job, "currency", None), "code", "IDR") or "IDR"
        kurs = getattr(job, "kurs_idr", None) or D1

        # TO display (simple; kalau kamu punya struktur company/contacts, tinggal ganti)
        customer = getattr(job, "customer", None)
        to_display = str(customer) if customer else "-"

        # ==========================
        # REVENUE (IDR)
        # sesuai contoh CargoChains: subtotal = job.total_amount
        # backup: job.total_in_idr (kalau kurs invalid)
        # ==========================
        sub_total = getattr(job, "total_amount", None) or D0
        backup_total_idr = getattr(job, "total_in_idr", None) or D0

        revenue_currency_amount = sub_total.quantize(Decimal("0.01"))

        if currency_code != "IDR":
            if kurs and kurs != D0:
                revenue_idr = (sub_total * kurs).quantize(Decimal("0.01"))
            else:
                revenue_idr = backup_total_idr.quantize(Decimal("0.01"))
        else:
            revenue_idr = sub_total.quantize(Decimal("0.01"))

        # ==========================
        # COGS (IDR) = SUM(JobCost.est_amount)
        # ==========================
        costs_qs = JobCost.objects.filter(job_order=job)
        if hasattr(JobCost, "is_active"):
            costs_qs = costs_qs.filter(is_active=True)

        if hasattr(JobCost, "sort_order"):
            costs_qs = costs_qs.order_by("sort_order", "id")
        else:
            costs_qs = costs_qs.order_by("id")

        items_cost_idr = costs_qs.aggregate(total=Sum("est_amount"))["total"] or D0
        total_cogs_idr = Decimal(items_cost_idr).quantize(Decimal("0.01"))

        # ==========================
        # GROSS PROFIT (IDR)
        # ==========================
        gross_profit_idr = (revenue_idr - total_cogs_idr).quantize(Decimal("0.01"))

        # ==========================
        # HEADER / FOOTER (reuse CargoChains standard)
        # ==========================
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

        # ==========================
        # BODY HTML
        # ==========================
        html = render_to_string(
            self.template_name,
            {
                "job": job,
                "to_display": to_display,
                "currency_code": currency_code,
                "kurs": kurs,
                "revenue_currency_amount": revenue_currency_amount, 
                "revenue_idr": revenue_idr,
                "costs": costs_qs,
                "items_cost_idr": items_cost_idr,
                "total_cogs_idr": total_cogs_idr,
                "gross_profit_idr": gross_profit_idr,

                "is_pdf": True,
            },
            request=request,
        )

        # DEBUG HTML kalau perlu
        if request.GET.get("html") == "1":
            os.unlink(tmp_header.name)
            os.unlink(tmp_footer.name)
            return HttpResponse(html)

        # ==========================
        # PDFKIT OPTIONS
        # ==========================
        options = {
            "page-size": "A4",
            "encoding": "UTF-8",

            "margin-top": "30mm",
            "margin-bottom": "45mm",
            "margin-left": "15mm",
            "margin-right": "15mm",

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

        filename = f"Profitability-{job.number}.pdf"
        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
