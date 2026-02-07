# sales/forms/sales_config.py
from django import forms
from sales.models import SalesConfig

class SalesConfigForm(forms.ModelForm):
    class Meta:
        model = SalesConfig
        fields = [
            "default_currency",
            "quotation_valid_days",
            "sales_fee_percent",
            "quotation_signature_source",
            "quotation_signature_user",
            "joborder_signature_source",
            "joborder_signature_user",
            "customer_note",
            "term_conditions",
        ]
        widgets = {
            "customer_note": forms.Textarea(attrs={"rows": 8}),
            "term_conditions": forms.Textarea(attrs={"rows": 10}),
            
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        for f in ["quotation_signature_source", "quotation_signature_user",
                  "joborder_signature_source", "joborder_signature_user"]:
            if f in self.fields:
                self.fields[f].widget.attrs.update({"class": "form-select"})

        # textareas
        for f in ["customer_note", "term_conditions"]:
            if f in self.fields:
                self.fields[f].widget.attrs.update({"class": "form-control"})
