from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from .forms import ProfitabilityFilterForm, COGSJournalFilterForm
from .services import ProfitabilityService, COGSJournalReportService
from django.shortcuts import get_object_or_404, redirect, render
from job.models.job_orders import JobOrder

class ProfitabilityReportView(LoginRequiredMixin, TemplateView):
    template_name = "reports/profitability.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        form = ProfitabilityFilterForm(self.request.GET or None)
        form.is_valid()

        cd = form.cleaned_data if form.is_bound else {}

        svc = ProfitabilityService(revenue_field="amount")  # kalau field kamu total_amount, ganti di sini
        rows, totals = svc.build(
            date_from=cd.get("date_from"),
            date_to=cd.get("date_to"),
            customer_id=cd.get("customer").id if cd.get("customer") else None,
            status=cd.get("status") or None,
            job_id=cd.get("job_id") or None,
        )

        ctx.update({
            "form": form,
            "rows": rows,
            "totals": totals,
        })
        return ctx



class JobProfitabilityDetailView(LoginRequiredMixin, TemplateView):
    template_name = "reports/job_profitability_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job_id = self.kwargs["job_id"]
        job = get_object_or_404(JobOrder, pk=job_id)

        svc = ProfitabilityService(revenue_field="amount")  # ganti kalau field revenue beda
        profit = svc.build_for_job(job)
        cogs_lines = svc.get_cogs_lines_for_job(job)
        cogs_journal_id = getattr(job, "complete_journal_id", None)

        ctx.update({
            "job": job,
            "profit": profit,
            "cogs_lines": cogs_lines,
            "cogs_journal_id": cogs_journal_id,
        })
        return ctx
    

class COGSJournalReportView(LoginRequiredMixin, TemplateView):
    template_name = "reports/cogs_journals.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        form = COGSJournalFilterForm(self.request.GET or None)
        form.is_valid()
        cd = form.cleaned_data if form.is_bound else {}

        svc = COGSJournalReportService()
        journals = svc.get_journals(
            date_from=cd.get("date_from"),
            date_to=cd.get("date_to"),
            posted_only=cd.get("posted_only") if cd.get("posted_only") is not None else True,
        )

        ctx.update({
            "form": form,
            "journals": journals,
        })
        return ctx
