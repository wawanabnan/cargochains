# accounting/forms/settings.py
from django import forms
from accounting.models.settings import AccountingSettings


class AccountingSettingsForm(forms.ModelForm):
    class Meta:
        model = AccountingSettings
        fields = [
            "active_fiscal_year",

            # ✅ JOB COSTING (OPSI B)
            "auto_create_job_costing_journal",
            "auto_post_job_costing_journal",
        ]
        widgets = {
            "active_fiscal_year": forms.NumberInput(attrs={
                "class": "form-control form-control-sm",
                "min": 2000,
                "max": 2100,
            }),
           "auto_create_job_costing_journal": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "role": "switch",
                "id": "id_auto_create",
            }),
            "auto_post_job_costing_journal": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "role": "switch",
                "id": "id_auto_post",
            }),
        }

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("auto_post_job_costing_journal") and not cleaned.get("auto_create_job_costing_journal"):
            raise forms.ValidationError(
                "Auto Post Job Costing Journal membutuhkan Auto Create aktif."
            )

        return cleaned
