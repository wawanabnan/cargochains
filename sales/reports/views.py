from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .services import SalesRevenueReportService


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

        ctx.update({
            "invoices": qs,
            "totals": totals,
        })
        return ctx
