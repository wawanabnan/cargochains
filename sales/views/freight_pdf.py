# sales/views/fq_pdf_html.py

import pdfkit
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.contrib.staticfiles import finders

from sales.freight import FreightQuotation


class FreightQuotationPdfHtmlView(LoginRequiredMixin, View):
    """
    Generate PDF Freight Quotation pakai wkhtmltopdf (HTML -> PDF).
    Layout diambil dari templates/sales/fq_print.html
    """

    def get(self, request, pk, *args, **kwargs):
        fq = get_object_or_404(FreightQuotation, pk=pk)

        # Cari file logo di static (static/img/logo.png)
        logo_file = finders.find("img/logo.png")
        logo_path = None
        if logo_file:
            # wkhtmltopdf butuh format file://
            logo_path = "file:///" + logo_file.replace("\\", "/")

        # Render HTML dari template surat resmi
        html = render_to_string(
            "sales/fq_print.html",
            {
                "fq": fq,
                "is_pdf": True,     # sembunyikan tombol Print/Close di PDF
                "logo_path": logo_path,
            },
        )

        # Options wkhtmltopdf
        options = {
            "page-size": "A4",
            "encoding": "UTF-8",
            "margin-top": "10mm",
            "margin-bottom": "10mm",
            "margin-left": "10mm",
            "margin-right": "10mm",
            # IZINKAN akses file://
            "enable-local-file-access": None,
        }

        # Konfigurasi path wkhtmltopdf
        wkhtml_path = getattr(settings, "WKHTMLTOPDF_CMD", None)
        config = pdfkit.configuration(wkhtmltopdf=wkhtml_path) if wkhtml_path else None

        pdf_data = pdfkit.from_string(
            html,
            False,               # False = return bytes, bukan simpan file
            options=options,
            configuration=config,
        )

        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="FQ-{fq.number}.pdf"'
        return response
