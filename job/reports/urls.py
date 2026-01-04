from django.urls import path
from .views import ProfitabilityReportView, COGSJournalReportView
from .views import ProfitabilityReportView, COGSJournalReportView, JobProfitabilityDetailView
from .view_pdf import JobProfitabilityPdfView\

app_name = "job_reports"

urlpatterns = [
    path("profitability/", ProfitabilityReportView.as_view(), name="profitability"),
    path("cogs-journals/", COGSJournalReportView.as_view(), name="cogs_journals"),
    path("profitability/<int:job_id>/", JobProfitabilityDetailView.as_view(), name="job_profitability_detail"),
    path("profitability/<int:job_id>/pdf/", JobProfitabilityPdfView.as_view(), name="job_profitability_pdf"),

]
