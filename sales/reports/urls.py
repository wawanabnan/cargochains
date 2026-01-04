from django.urls import path
from .views import SalesRevenueReportView

app_name = "sales_reports"

urlpatterns = [
    path("revenue/", SalesRevenueReportView.as_view(), name="revenue"),
]
