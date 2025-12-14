from django import forms
from partners.models import Partner

class CustomerContactForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = [
            "name", "job_title", "email", "phone", "mobile",
            "is_sales_contact", "is_billing_contact",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # styling AdminLTE/Bootstrap
        for name, field in self.fields.items():
            w = field.widget
            css = w.attrs.get("class", "")
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = (css + " form-check-input").strip()
            else:
                w.attrs["class"] = (css + " form-control").strip()

        # label ringkas
        self.fields["is_sales_contact"].label = "Sales Contact"
        self.fields["is_billing_contact"].label = "Billing Contact"
