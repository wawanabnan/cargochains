from django import forms
from django.forms import inlineformset_factory

from billing.models.vendor_bills import VendorBill, VendorBillLine
from core.models.taxes import Tax   # sesuaikan path model Tax


# =========================
# Header Form
# =========================
class VendorBillForm(forms.ModelForm):
    class Meta:
        model = VendorBill
        fields = (
            "bill_number", "bill_date", "due_date",
            "vendor", "currency", "idr_rate",
            "notes",
        )
        widgets = {
            "bill_number": forms.TextInput(attrs={"class": "form-control"}),
            "bill_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),

            "vendor": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "idr_rate": forms.TextInput(attrs={"class": "form-control"}),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
        }


# =========================
# Line Form
# =========================
class VendorBillLineForm(forms.ModelForm):
    class Meta:
        model = VendorBillLine
        fields = ("vendor_booking", "description", "amount", "taxes")
        widgets = {
            "vendor_booking": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={
                "class": "form-control text-end",
                "step": "0.01",
            }),

            # M2M taxes (Bootstrap 5 style)
            "taxes": forms.SelectMultiple(attrs={
                "class": "form-select",
                "multiple": True,
                "size": 3,   # biar nggak kepanjangan
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # booking optional
        if "vendor_booking" in self.fields:
            self.fields["vendor_booking"].required = False
            self.fields["vendor_booking"].empty_label = "-- optional --"

        # taxes optional
        if "taxes" in self.fields:
            self.fields["taxes"].required = False
            # filter pajak aktif kalau ada
            # self.fields["taxes"].queryset = Tax.objects.filter(is_active=True)


# =========================
# Formset
# =========================
VendorBillLineFormSet = inlineformset_factory(
    VendorBill,
    VendorBillLine,
    form=VendorBillLineForm,
    extra=1,
    can_delete=True,
)
