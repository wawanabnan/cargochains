# core/forms/currencies.py
from django import forms
from core.models.currencies import Currency

class CurrencyForm(forms.ModelForm):
    class Meta:
        model = Currency
        fields = ["code", "name", "symbol", "is_active"]  # ✅ sesuaikan jika beda

        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "IDR"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Indonesian Rupiah"}),
            "symbol": forms.TextInput(attrs={"class": "form-control", "placeholder": "Rp"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
