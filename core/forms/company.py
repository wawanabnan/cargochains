from django import forms
from core.models.company import CompanyProfile
from geo.models import Location


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            # mandatory identity
            "name",
            "brand",

            # address lines (mandatory address_1)
            "address_1",
            "address_2",

            # geo
            "country",
            "province",
            "regency",
            "district",
            "postal_code",

            # contact
            "phone",
            "email",

            # finance/legal
            "default_currency",
            "npwp",
            "is_pkp",

            # branding
            "logo",
            "footer_text",

            # flags
            "enable_multi_currency",
            "enable_tax",
            "enable_job_cost",
            "enable_auto_journal",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "brand": forms.TextInput(attrs={"class": "form-control form-control-sm"}),

            "address_1": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "address_2": forms.TextInput(attrs={"class": "form-control form-control-sm"}),

            # geo selects
            "country": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "province": forms.Select(attrs={"class": "form-select form-select-sm", "data-role": "province"}),
            "regency": forms.Select(attrs={"class": "form-select form-select-sm", "data-role": "regency"}),
            "district": forms.Select(attrs={"class": "form-select form-select-sm", "data-role": "district"}),

            "postal_code": forms.TextInput(attrs={"class": "form-control form-control-sm"}),

            "phone": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "email": forms.EmailInput(attrs={"class": "form-control form-control-sm"}),

            "default_currency": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "npwp": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "footer_text": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        
        # Checkbox styling
        for f in ("is_pkp", "enable_multi_currency", "enable_tax", "enable_job_cost", "enable_auto_journal"):
            if f in self.fields:
                self.fields[f].widget.attrs.update({"class": "form-check-input"})

        # OPTIONAL UX:
        # country biasanya default Indonesia & tidak perlu diubah user
        # Kalau om mau dikunci di UI:
        # self.fields["country"].disabled = True

        # ...
        indo = Location.objects.filter(kind="country", name__iexact="Indonesia", status="active").first()
        if "country" in self.fields:
            if indo and (self.instance is None or not getattr(self.instance, "country_id", None)):
                self.fields["country"].initial = indo.id
            
            self.fields["country"].disabled = True


        if "province" in self.fields:
            if indo:
                self.fields["province"].queryset = Location.objects.filter(parent=indo, status="active").order_by("name")
            else:
                self.fields["province"].queryset = Location.objects.none()

        # regency children of province
        if "regency" in self.fields:
            if self.instance and self.instance.province_id:
                self.fields["regency"].queryset = Location.objects.filter(parent_id=self.instance.province_id, status="active").order_by("name")
            else:
                self.fields["regency"].queryset = Location.objects.none()

        
        # district children of regency
        if "district" in self.fields:
            if self.instance and self.instance.regency_id:
                self.fields["district"].queryset = Location.objects.filter(parent_id=self.instance.regency_id, status="active").order_by("name")
            else:
                self.fields["district"].queryset = Location.objects.none()
