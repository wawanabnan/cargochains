# billing/forms/vendor_payment.py
from django import forms
from django.forms import inlineformset_factory

from billing.models.vendor_payment import VendorPayment, VendorPaymentLine
from partners.models import Vendor
from core.models.currencies import Currency
from accounting.models.chart import Account

class VendorPaymentForm(forms.ModelForm):
    class Meta:
        model = VendorPayment
        fields = [
            "vendor", "payment_date",
            "currency", "idr_rate",
            "cash_account",
            "reference", "memo",
        ]
        widgets = {
            "vendor": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "payment_date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),

            "currency": forms.Select(attrs={"class": "form-select form-select-sm", "id": "id_currency"}),
            "idr_rate": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.000001", "id": "id_idr_rate"}),

            "cash_account": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "reference": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "memo": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["currency"].queryset = Currency.objects.all().order_by("code")

        # filter bank/cash account (sesuaikan filter Account om)
        self.fields["cash_account"].queryset = Account.objects.order_by("code")


class VendorPaymentLineForm(forms.ModelForm):
    class Meta:
        model = VendorPaymentLine
        fields = ["vendor_bill", "description", "amount"]
        widgets = {
            "vendor_bill": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "description": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "amount": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
        }


VendorPaymentLineFormSet = inlineformset_factory(
    VendorPayment,
    VendorPaymentLine,
    form=VendorPaymentLineForm,
    extra=1,
    can_delete=True,
)
