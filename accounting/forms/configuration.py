from django import forms
from accounting.models.settings import AccountingSettings

class AccountingConfigurationForm(forms.ModelForm):
    class Meta:
        model = AccountingSettings
        fields = [
            "active_fiscal_year",
            "posting_policy",

            "default_ar_account",
            "default_sales_account",
            "default_tax_account",

            "default_cash_account",
            "default_pph_account",

            "auto_create_job_costing_journal",
            "auto_post_job_costing_journal",
        ]
        widgets = {
            "active_fiscal_year": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
            "posting_policy": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "default_ar_account": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "default_sales_account": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "default_tax_account": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "default_cash_account": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "default_pph_account": forms.Select(attrs={"class": "form-select form-select-sm"}),

             "auto_create_job_costing_journal": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "role": "switch",
            }),
            "auto_post_job_costing_journal": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "role": "switch",
            }),
        }
