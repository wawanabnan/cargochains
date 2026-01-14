from django.db import models
from decimal import Decimal
from django import forms
from shipments.models.vendor_bookings import VendorBooking
from core.models.payment_terms import PaymentTerm

discount_amount = models.DecimalField(
    max_digits=18,
    decimal_places=2,
    default=Decimal("0.00"),
    help_text="Discount amount (authoritative)"
)

class VendorBookingForm(forms.ModelForm):
    
    class Meta:
        model = VendorBooking
        fields = [
            "issued_date",
            "vendor",
            "currency",
            'payment_term',
            'currency',
            "idr_rate",
            "discount_amount"
            
        ]
        widgets = {
            "issued_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control form-control-sm",
                }
            ),
            "vendor": forms.Select(
                attrs={
                    "class": "form-select form-select-sm",
                }
            ),
            "payment_term": forms.Select(
                attrs={
                    "class": "form-select form-select-sm",
                }
            ),
            "currency": forms.Select(
                attrs={
                    "class": "form-select form-select-sm",
                }
            ),

            "idr_rate": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "step": "0.000001",
                }
            ),
             "discount_amount": forms.NumberInput(
                attrs={"class": "form-control form-control-sm text-end", "step": "0.01", "placeholder": "Amount"}
            ),
         
           
        }

    def clean(self):
        cleaned = super().clean()

        currency = cleaned.get("currency")
        idr_rate = cleaned.get("idr_rate")
        discount_amount = cleaned.get("discount_amount")

        if currency and idr_rate in (None, ""):
            self.add_error(
                "idr_rate",
                "IDR rate wajib diisi jika currency dipilih."
            )

        if not self.cleaned_data.get("idr_rate"):
            self.cleaned_data["idr_rate"] = Decimal("1")

        

        if discount_amount is not None and discount_amount < 0:
            self.add_error(
                "discount_amount",
                "Discount amount tidak boleh negatif."
            )

        return cleaned
    


from django import forms
from django.forms import inlineformset_factory

from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine
from core.models.taxes import Tax

class VendorBookingLineForm(forms.ModelForm):
  
    class Meta:
        model = VendorBookingLine
        fields = [
            "cost_type",
            "description",
            "qty",
            "uom",
            "unit_price",
            "details",
            "taxes",
            
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 1, "readonly": "readonly"}),
            "qty": forms.NumberInput(attrs={"class": "form-control form-control-sm text-end", "step": "0.0001"}),
            "uom": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control form-control-sm text-end", "step": "0.01"}),
            "details": forms.HiddenInput(),
            
            
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["description"].widget.attrs["readonly"] = "readonly"
        self.fields["description"].widget.attrs.setdefault("class", "form-control form-control-sm auto-grow")

        # taxes M2M - pakai select2 ajax
        self.fields["taxes"].queryset = Tax.objects.all().order_by("name")
        self.fields["taxes"].widget = forms.SelectMultiple(attrs={
            "class": "form-select form-select-sm js-tax-select2",
            "data-placeholder": "Select tax...",
            "data-ajax-url": "/taxes/autocomplete/",  # URL endpoint kita buat
        })
        self.fields["taxes"].required = False



VendorBookingLineFormSet = inlineformset_factory(
    VendorBooking,
    VendorBookingLine,
    form=VendorBookingLineForm,
    extra=0,          # tampilkan line yang ada saja
    can_delete=True,
)
