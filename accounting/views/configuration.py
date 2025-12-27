from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Count
from django.urls import reverse
from django.views.generic import TemplateView

from accounting.forms.configuration import AccountingConfigurationForm
from accounting.models.chart import Account
from accounting.models.journal import Journal
from accounting.models.period_lock import AccountingPeriodLock
from accounting.models.settings import AccountingSettings


class AccountingConfigurationView(LoginRequiredMixin, TemplateView):
    template_name = "settings/configuration.html"

    def get(self, request, *args, **kwargs):
        # ensure singleton exists
        AccountingSettings.get_solo()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        settings_obj = AccountingSettings.get_solo()
        old_year = settings_obj.active_fiscal_year

        form = AccountingConfigurationForm(request.POST, instance=settings_obj)
        if form.is_valid():
            new_obj = form.save()

            # Guard UX: FY berubah tapi COA FY baru kosong
            coa_exists = Account.objects.filter(chart_year=new_obj.active_fiscal_year).exists()
            if old_year != new_obj.active_fiscal_year and not coa_exists:
                messages.warning(
                    request,
                    f"Active Fiscal Year berubah ke {new_obj.active_fiscal_year}, tetapi COA untuk FY tersebut belum ada. "
                    "Silakan import COA sebelum membuat journal."
                )
            else:
                messages.success(request, "Accounting configuration updated.")
            return self.get(request, *args, **kwargs)

        # kalau invalid, tetap render dengan status panel
        ctx = self.get_context_data(**kwargs)
        ctx["form"] = form
        return self.render_to_response(ctx)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        settings_obj = AccountingSettings.get_solo()
        active_year = settings_obj.active_fiscal_year

        # untuk status summary: total COA FY aktif (boleh include group)
        coa_qs = (
            Account.objects
            .filter(chart_year=active_year, is_active=True)
            .order_by("code")
        )
        coa_count = coa_qs.count()
        coa_ready = coa_count > 0

        # ✅ untuk dropdown mapping: WAJIB postable
        coa_postable_qs = (
            Account.objects
            .filter(chart_year=active_year, is_active=True, is_postable=True)
            .order_by("code")
        )

        journal_count = Journal.objects.count()

        last_locked_obj = (
            AccountingPeriodLock.objects.filter(is_locked=True).order_by("-year", "-month").first()
        )

        status = (
            ("READY", "success", "🟢 Ready")
            if coa_ready else
            ("NOT_READY", "danger", "🔴 Not Ready (COA missing for active FY)")
        )

        # build form dulu
        form = AccountingConfigurationForm(instance=settings_obj)

        # filter dropdown mapping by Active FY + postable
        account_fields = (
            "default_ar_account",
            "default_sales_account",
            "default_tax_account",
            "default_cash_account",
            "default_pph_account",
        )
        for f in account_fields:
            if f in form.fields:
                form.fields[f].queryset = coa_postable_qs
                form.fields[f].required = False

        ctx.update({
            "form": form,
            "settings_obj": settings_obj,
            "active_year": active_year,
            "coa_count": coa_count,
            "coa_ready": coa_ready,
            "journal_count": journal_count,
            "last_locked": last_locked_obj,
            "acct_status": status,
        })
        return ctx
