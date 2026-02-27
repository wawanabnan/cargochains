from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .services import SalesRevenueReportService
from django.db import models

from billing.models.customer_invoice import Invoice
from django.db.models import Value
from partners.models import Customer
from core.models.currencies import Currency

class SalesRevenueReportView(LoginRequiredMixin, TemplateView):
    template_name = "reports/screen/sales_revenue.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        svc = SalesRevenueReportService()

        qs, totals = svc.build(
            date_from=self.request.GET.get("date_from"),
            date_to=self.request.GET.get("date_to"),
            customer_id=self.request.GET.get("customer"),
            currency=self.request.GET.get("currency"),
        )

        currencies = Currency.objects.order_by(
            models.Case(
                models.When(code="IDR", then=0),
                default=1,
                output_field=models.IntegerField(),
            ),
            "code",
        )


        ctx.update({
            "invoices": qs,
            "totals": totals,
            "currencies":currencies

        })
        return ctx




import pdfkit
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View



class SalesRevenueReportPdfView(View):
    template_name = "reports/pdf/sales_revenue_pdf.html"

    def get(self, request, *args, **kwargs):
        svc = SalesRevenueReportService()

        qs, totals = svc.build(
            date_from=request.GET.get("date_from"),
            date_to=request.GET.get("date_to"),
            currency=request.GET.get("currency"),
        )

        html = render_to_string(
            self.template_name,
            {
                "invoices": qs,
                "totals": totals,
                "request": request,
            },
            request=request,
        )

        options = {
            "page-size": "A4",
            "orientation": "portrait",
            "encoding": "UTF-8",
            "margin-top": "8mm",
            "margin-right": "8mm",
            "margin-bottom": "10mm",
            "margin-left": "8mm",
            "enable-local-file-access": None,
        }

        # 🔥 INI KUNCINYA — SAMA PERSIS DENGAN VIEW PDF YANG SUDAH JALAN
        config = pdfkit.configuration(
            wkhtmltopdf=settings.WKHTMLTOPDF_CMD
        )

        pdf = pdfkit.from_string(
            html,
            False,
            options=options,
            configuration=config,
        )

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="sales_revenue_report.pdf"'
        return response