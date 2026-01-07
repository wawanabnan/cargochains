from django import forms
from core.models.company import CompanyProfile

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            "name", "brand", "phone", "email", "website",
            "address_1", "address_2",
            "country", "province", "regency", "district",
            "postal_code",
            "logo",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "brand": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "phone": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "email": forms.EmailInput(attrs={"class":"form-control form-control-sm"}),
            "website": forms.URLInput(attrs={"class":"form-control form-control-sm"}),
            "address_1": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "address_2": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "country": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "province": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "regency": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "district": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
            "postal_code": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
        }

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            required_fields = [
                "name",
                "address_1",
                "country",
                "province",
                "regency",
                "district",
                "postal_code",
            ]
            for f in required_fields:
                if f in self.fields:
                    self.fields[f].required = True



from django import forms
from core.models.company import CompanyProfile  # sesuaikan path
from core.models.currencies import Currency

class CompanyForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            "name", "brand",
            "phone", "email", "website",
            "address_1", "address_2",
            "country", "province", "regency", "district",
            "postal_code",
            "npwp", "is_pkp",
            "logo",
            "footer_text",
            "default_currency",
            "enable_multi_currency",
            "enable_tax",
            "enable_job_cost",
            "enable_auto_journal",
            "is_default",
        ]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),

            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),

            "address_1": forms.TextInput(attrs={"class": "form-control"}),
            "address_2": forms.TextInput(attrs={"class": "form-control"}),

            "country": forms.TextInput(attrs={"class": "form-control"}),
            "province": forms.TextInput(attrs={"class": "form-control"}),
            "regency": forms.TextInput(attrs={"class": "form-control"}),
            "district": forms.TextInput(attrs={"class": "form-control"}),

            "postal_code": forms.TextInput(attrs={"class": "form-control"}),

            "npwp": forms.TextInput(attrs={"class": "form-control"}),
            "footer_text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),

            "default_currency": forms.Select(attrs={"class": "form-select"}),

            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),

            "enable_job_cost": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "enable_auto_journal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "enable_multi_currency": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "enable_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_pkp": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # optional: hanya currency aktif
        try:
            self.fields["default_currency"].queryset = Currency.objects.filter(is_active=True).order_by("code")
        except Exception:
            pass
