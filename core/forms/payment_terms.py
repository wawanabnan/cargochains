# core/forms/payment_terms.py
from django import forms
from core.models.payment_terms import PaymentTerm


class PaymentTermForm(forms.ModelForm):
    class Meta:
        model = PaymentTerm
        fields = [
            "code", "name", "days", "dp_percent",
            "is_active", "is_default", "sort_order",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "NET30"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Net 30 Days"}),
            "days": forms.NumberInput(attrs={"class": "form-control form-control-sm", "min": 0}),
            "dp_percent": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01", "min": 0}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip().upper()
