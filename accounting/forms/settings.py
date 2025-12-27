from django import forms
from accounting.models.settings import AccountingSettings


class AccountingSettingsForm(forms.ModelForm):
    class Meta:
        model = AccountingSettings
        fields = ["active_fiscal_year"]
        widgets = {
            "active_fiscal_year": forms.NumberInput(attrs={
                "class": "form-control form-control-sm",
                "min": 2000,
                "max": 2100,
            })
        }
