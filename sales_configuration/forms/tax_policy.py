from django import forms
from core.models.taxes import Tax
from sales_configuration.models import SalesTaxPolicy


class SalesTaxConfigForm(forms.Form):
    """
    Form konfigurasi pajak sales per module.
    """
    MODULE_CHOICES = SalesTaxPolicy.MODULE_CHOICES

    module = forms.ChoiceField(
        choices=MODULE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"})
    )

    taxes = forms.ModelMultipleChoiceField(
        queryset=Tax.objects.filter(is_active=True, category__code="PPN"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Active Taxes"
    )

    default_tax = forms.ModelChoiceField(
        queryset=Tax.objects.filter(is_active=True, category__code="PPN"),
        required=False,
        label="Default Tax",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"})
    )

    def __init__(self, *args, **kwargs):
        module = kwargs.pop("module", None)
        super().__init__(*args, **kwargs)

        # styling checkbox
        self.fields["taxes"].widget.attrs.update({"class": "form-check-input"})

        if module:
            self.fields["module"].initial = module

            # aktifkan checkbox sesuai policy
            active = Tax.objects.filter(
                sales_policies__module=module,
                sales_policies__is_active=True,
            )
            self.fields["taxes"].initial = active

            default = Tax.objects.filter(
                sales_policies__module=module,
                sales_policies__is_default=True,
            ).first()
            self.fields["default_tax"].initial = default
