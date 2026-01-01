from django import forms
from core.models.company import CompanyProfile


class SetupBasicsForm(forms.ModelForm):
    """
    Step 2: Minimal finance defaults
    - default_currency (optional)
    - npwp, is_pkp (optional)
    - footer_text (optional)
    """
    class Meta:
        model = CompanyProfile
        fields = ["default_currency", "npwp", "is_pkp", "footer_text"]
        widgets = {
            "default_currency": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "npwp": forms.TextInput(attrs={"class": "form-control form-control-sm", "autocomplete": "off"}),
            "is_pkp": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "footer_text": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 3}),
        }


class SetupFeaturesForm(forms.ModelForm):
    """
    Step 3: Feature flags (saklar ON/OFF fitur)
    """
    class Meta:
        model = CompanyProfile
        fields = ["enable_tax", "enable_multi_currency", "enable_job_cost", "enable_auto_journal"]
        widgets = {
            "enable_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "enable_multi_currency": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "enable_job_cost": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "enable_auto_journal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
