from django.urls import path
from .views import SalesRevenueReportView,SalesRevenueReportPdfView

app_name = "sales_reports"

urlpatterns = [
    path("revenue/", SalesRevenueReportView.as_view(), name="revenue"),
    path("revenue/pdf/", SalesRevenueReportPdfView.as_view(), name="revenue_pdf"),
]
