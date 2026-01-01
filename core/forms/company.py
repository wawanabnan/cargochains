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
