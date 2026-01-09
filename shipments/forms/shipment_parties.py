# shipments/forms.py
from django import forms
from shipments.models.shipments import Shipment
from partners.models import Partner

class ShipmentPartiesForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ["shipper", "consignee", "carrier", "agency", "cargo_description"]
        widgets = {
            "shipper":   forms.Select(attrs={"class": "form-select select2-partner", "data-url": "/partners/autocomplete/"}),
            "consignee": forms.Select(attrs={"class": "form-select select2-partner", "data-url": "/partners/autocomplete/"}),
            "carrier":   forms.Select(attrs={"class": "form-select select2-partner", "data-url": "/partners/autocomplete/"}),
            "agency":    forms.Select(attrs={"class": "form-select select2-partner", "data-url": "/partners/autocomplete/"}),
            "cargo_description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        so = kwargs.pop("sales_order", None)
        super().__init__(*args, **kwargs)
        # Default: kalau shipper kosong → isi dengan customer dari SO
        if so and not self.instance.pk and not self.initial.get("shipper") and not getattr(self.instance, "shipper_id", None):
            self.fields["shipper"].initial = getattr(getattr(so, "customer", None), "pk", None)

    def clean_shipper(self):
        shipper = self.cleaned_data.get("shipper")
        # Jika masih kosong, fallback ke customer SO
        so = getattr(self.instance, "sales_order", None)
        if not shipper and so and getattr(so, "customer_id", None):
            return so.customer
        return shipper
