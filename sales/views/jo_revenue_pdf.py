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

from sales.job_order_model import JobOrder, JobCost


D0 = Decimal("0.00")
D1 = Decimal("1.00")


class JobOrderRevenuePdfView(LoginRequiredMixin, View):
    template_name = "job_orders/jo_pdf.html"

    def get(self, request, pk):
        job = get_object_or_404(JobOrder, pk=pk)

        # ==========================
        # BASE DATA
        # ==========================
        currency_code = getattr(job.currency, "code", "IDR") or "IDR"
        kurs = job.kurs_idr or D1

        # ==========================
        # TO (company_name + billing contact)
        # self relation: Partner.company -> contacts
        # ==========================
        customer = job.customer
        company = customer.company if getattr(customer, "company_id", None) else customer
        company_name = company.company_name or company.name

        billing_contact = (
            company.contacts.filter(is_billing_contact=True).order_by("id").first()
        )

        if billing_contact:
            to_display = f"{company_name} - Attn: {billing_contact.name}"
        else:
            to_display = company_name

        # ==========================
        # REVENUE (IDR) = SUBTOTAL * KURS
        # subtotal field = total_amount (bukan grand_total)
        # total_in_idr hanya backup jika kurs invalid/0 (non-IDR)
        # ==========================
        sub_total = job.total_amount or D0
        backup_total_idr = job.total_in_idr or D0

        if currency_code != "IDR":
            if kurs and kurs != D0:
                revenue_idr = (sub_total * kurs).quantize(Decimal("0.01"))
            else:
                revenue_idr = backup_total_idr.quantize(Decimal("0.01"))
        else:
            revenue_idr = sub_total.quantize(Decimal("0.01"))

        # ==========================
        # COGS (IDR) = SUM(JobCost.amount) ONLY
        # (TIDAK ADA TAX DI COGS)
        # ==========================
        costs_qs = JobCost.objects.filter(job_order=job).order_by("id")
        items_cost_idr = costs_qs.aggregate(total=Sum("amount"))["total"] or D0
        total_cogs_idr = Decimal(items_cost_idr).quantize(Decimal("0.01"))

        # ==========================
        # GROSS PROFIT (IDR)
        # ==========================
        gross_profit_idr = (revenue_idr - total_cogs_idr).quantize(Decimal("0.01"))

        # ==========================
        # TAX/PPH IDR (OPSIONAL: buat display saja, bukan COGS)
        # ==========================
        tax_amount = job.tax_amount or D0
        pph_amount = job.pph_amount or D0

        if currency_code != "IDR":
            tax_idr = (tax_amount * kurs).quantize(Decimal("0.01")) if kurs and kurs != D0 else D0
            pph_idr = (pph_amount * kurs).quantize(Decimal("0.01")) if kurs and kurs != D0 else D0
        else:
            tax_idr = tax_amount.quantize(Decimal("0.01"))
            pph_idr = pph_amount.quantize(Decimal("0.01"))

        # ==========================
        # WKHTML HEADER/FOOTER
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
                "currency_code": currency_code,
                "kurs": kurs,

                "to_display": to_display,

                # Revenue & Costing
                "revenue_idr": revenue_idr,
                "costs": costs_qs,
                "items_cost_idr": items_cost_idr,
                "total_cogs_idr": total_cogs_idr,
                "gross_profit_idr": gross_profit_idr,

                # Optional display only
                "tax_idr": tax_idr,
                "pph_idr": pph_idr,

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
