from django import forms
from django.forms import inlineformset_factory
from . import models as m

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = m.PurchaseOrder
        fields = [
            "vendor",
            "order_date", "expected_date",
            "currency",
            "discount_amount", "tax_percent",
            "ref_number", "notes", "attachment",
            "status",
        ]
        widgets = {
            "order_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expected_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # HANYA vendor: gunakan role_type (bukan role)
        self.fields["vendor"].queryset = (
            self.fields["vendor"].queryset
            .select_related("partner", "role_type")
            .filter(role_type__code="vendor")
        )
        # Label rapi: "Partner Name (Role Name)"
        self.fields["vendor"].label_from_instance = (
            lambda obj: f"{obj.partner.name} ({obj.role_type.name})"
        )

        # Styling umum
        for name, f in self.fields.items():
            if not isinstance(f.widget, (forms.CheckboxInput, forms.ClearableFileInput)):
                f.widget.attrs.setdefault("class", "form-control")
        self.fields["discount_amount"].widget.attrs.setdefault("step", "0.01")
        self.fields["tax_percent"].widget.attrs.setdefault("step", "0.01")


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = m.PurchaseOrderLine
        fields = ["line_no", "product_name", "description", "uom", "qty", "unit_price", "line_discount"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            if not isinstance(f.widget, (forms.CheckboxInput,)):
                f.widget.attrs.setdefault("class", "form-control")
        self.fields["qty"].widget.attrs.setdefault("step", "0.001")
        self.fields["unit_price"].widget.attrs.setdefault("step", "0.01")
        self.fields["line_discount"].widget.attrs.setdefault("step", "0.01")


PurchaseOrderLineFormSet = inlineformset_factory(
    parent_model=m.PurchaseOrder,
    model=m.PurchaseOrderLine,
    form=PurchaseOrderLineForm,
    extra=1,
    can_delete=True,
    fk_name="purchase_order",  # pastikan target FK benar
)
