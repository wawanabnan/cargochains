from django import forms

from job.models.costs import JobCostType
from accounting.models.chart import Account
from accounting.models.settings import AccountingSettings


class JobCostTypeForm(forms.ModelForm):
    def __init2__(self, *args, **kwargs):
        # ✅ FIX: terima request dari CBV (get_form_kwargs)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # ✅ filter account sesuai active fiscal year
        year = None
        try:
            year = AccountingSettings.get_solo().active_fiscal_year
        except Exception:
            year = None

        qs = Account.objects.filter(is_active=True, is_postable=True)
        if year:
            qs = qs.filter(chart_year=year)

        # Kalau field cogs_account ada di model & dimasukin ke fields Meta, ini akan jalan.
        if "cogs_account" in self.fields:
            self.fields["cogs_account"].queryset = qs
            self.fields["cogs_account"].required = False

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        year = AccountingSettings.get_solo().active_fiscal_year

        qs = Account.objects.filter(
            is_active=True,
            is_postable=True,     # ← hanya anak
            type="expense",
            chart_year=year,
            code__startswith="51",  # ← hanya COGS
        ).order_by("code")

        self.fields["cogs_account"].queryset = qs

    class Meta:
        model = JobCostType
        fields = [
            "code",
            "name",
            "cost_group",
            "requires_vendor",
            "cogs_account",     # ✅ TAMBAH: mapping ke COGS account
            "sort_order",
            "is_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),

            "cost_group": forms.TextInput(attrs={
                "class": "form-control form-control-sm",
                "placeholder": "vendor_trucking / vendor_freight / vendor_port / internal_misc"
            }),

            "requires_vendor": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "cogs_account": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "sort_order": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


