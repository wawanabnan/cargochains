# sales/views/fo_pdf_html.py (atau di file views freight om)

import pdfkit
import tempfile
import os

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views import View

from sales.freight import FreightOrder


class FreightOrderPdfHtmlView(LoginRequiredMixin, View):
    """
    Generate PDF Freight Order pakai wkhtmltopdf (HTML -> PDF)
    dengan header & footer letterhead.
    """

    def get(self, request, pk, *args, **kwargs):
        fo = get_object_or_404(FreightOrder, pk=pk)

        # ============================================
        # 1) ABSOLUTE URL ke gambar header & footer
        # ============================================
        header_url = request.build_absolute_uri(
            static("img/letter_header_bg.png")
        )
        footer_url = request.build_absolute_uri(
            static("img/letter_footer_bg.png")
        )

        # ============================================
        # 2) Render HTML untuk header & footer
        # ============================================
        header_html = render_to_string(
            "sales/pdf/header.html",
            {"header_url": header_url},
        )
        footer_html = render_to_string(
            "sales/pdf/footer.html",
            {"footer_url": footer_url},
        )

        # simpan ke file sementara (wkhtmltopdf butuh path file)
        tmp_header = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp_footer = tempfile.NamedTemporaryFile(delete=False, suffix=".html")

        tmp_header.write(header_html.encode("utf-8"))
        tmp_footer.write(footer_html.encode("utf-8"))

        tmp_header.close()
        tmp_footer.close()

        # ============================================
        # 3) Render BODY FO (konten saja)
        # ============================================
        body_html = render_to_string(
            "sales/fo_print.html",
            {
                "fo": fo,
                "is_pdf": True,
            },
        )

        # ============================================
        # 4) Options wkhtmltopdf
        # ============================================
        options = {
            "page-size": "A4",
            "encoding": "UTF-8",

            # area header/footer (sesuaikan dengan tinggi gambar)
            "margin-top": "30mm",     # ruang untuk header image
            "margin-bottom": "45mm",  # ruang untuk footer image

            # header/footer mau full-bleed: margin kiri/kanan 0
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

        pdf_data = pdfkit.from_string(
            body_html,
            False,
            options=options,
            configuration=config,
        )

        # beres: hapus file sementara
        os.unlink(tmp_header.name)
        os.unlink(tmp_footer.name)

        filename = f"SO-{fo.number}.pdf" if getattr(fo, "number", None) else "FreightOrder.pdf"

        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
