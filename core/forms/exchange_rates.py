
from django import forms
from core.models.exchange_rates import ExchangeRate
from core.models.currencies import Currency

class ExchangeRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ["rate_date", "currency", "rate_to_idr", "source", "is_active"]

        widgets = {
            "rate_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "rate_to_idr": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "min": "0"}),
            "source": forms.TextInput(attrs={"class": "form-control", "placeholder": "MANUAL / BI / ..."}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # tampilkan currency aktif saja (opsional)
        try:
            self.fields["currency"].queryset = Currency.objects.filter(is_active=True).order_by("code")
        except Exception:
            pass

    def clean_rate_to_idr(self):
        v = self.cleaned_data.get("rate_to_idr")
        if v is None or v <= 0:
            raise forms.ValidationError("Rate to IDR harus > 0.")
        return v
