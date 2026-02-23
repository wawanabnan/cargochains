# sales/forms/sales_config.py
from django import forms
from sales.models import SalesConfig


class SalesConfigForm(forms.ModelForm):
    class Meta:
        model = SalesConfig
        fields = [
            # General
            "default_currency",
            "quotation_valid_days",
            "sales_fee_percent",
            "bank_transfer_info",
            "default_payment_term",
            # Quotation
            "quotation_signature_source",
            "quotation_signature_user",
            "customer_note",
            "term_conditions",

            # Job Order
            "joborder_signature_source",
            "joborder_signature_user",

            # Service Order
            "vendor_note",  # ✅ typo fixed (was vemdor_note)
            "service_order_term_conditions",
            "service_order_signature_source",
            "service_order_signature_user",

            # OPTIONAL (kalau model kamu ada field default khusus SO)
            # "service_order_vendor_note_default",
        ]

        widgets = {
            "customer_note": forms.Textarea(attrs={"rows": 8}),
            "term_conditions": forms.Textarea(attrs={"rows": 10}),

            "vendor_note": forms.Textarea(attrs={"rows": 8}),
            "service_order_term_conditions": forms.Textarea(attrs={"rows": 10}),
            "bank_transfer_info": forms.Textarea(attrs={
                "class":"form-control",
                "rows": 4,
                "style": "min-height:auto;",
            }),

            # OPTIONAL:
            # "service_order_vendor_note_default": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # default_currency
        if "default_currency" in self.fields:
            self.fields["default_currency"].widget.attrs.update({
                "class": "form-control",
                "placeholder": "IDR",
            })

        
    

        # numeric inputs
        if "quotation_valid_days" in self.fields:
            self.fields["quotation_valid_days"].widget.attrs.update({
                "class": "form-control",
                "min": "0",
                "inputmode": "numeric",
            })

        if "sales_fee_percent" in self.fields:
            self.fields["sales_fee_percent"].widget.attrs.update({
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            })

        # selects
        for f in [
            "quotation_signature_source",
            "quotation_signature_user",
            "joborder_signature_source",
            "joborder_signature_user",
            "service_order_signature_source",
            "service_order_signature_user",
            "default_payment_term",
        ]:
            if f in self.fields:
                self.fields[f].widget.attrs.update({"class": "form-select"})

        # textareas
        for f in [
            "customer_note",
            "term_conditions",
            "vendor_note",
            "service_order_term_conditions",
            # OPTIONAL:
            # "service_order_vendor_note_default",
        ]:
            if f in self.fields:
                self.fields[f].widget.attrs.update({"class": "form-control"})
