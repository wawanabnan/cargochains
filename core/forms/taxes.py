from django import forms
from core.models.taxes import Tax, TaxCategory
from accounting.models.chart import Account  # sesuaikan path
from django.db.models import Q


class TaxCategoryForm(forms.ModelForm):
    class Meta:
        model = TaxCategory
        fields = ["code", "name", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control form-control-sm", "autocomplete": "off"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm", "autocomplete": "off"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TaxForm(forms.ModelForm):
    class Meta:
        model = Tax
        fields = [
            "category", "name", "code", "rate", "usage",
            "output_account", "input_account",
            "is_withholding", "is_active",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm", "autocomplete": "off"}),
            "code": forms.TextInput(attrs={"class": "form-control form-control-sm", "autocomplete": "off"}),
            "rate": forms.NumberInput(attrs={"class": "form-control form-control-sm text-end", "step": "0.01"}),
            "usage": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "output_account": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "input_account": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "is_withholding": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        chart_year = kwargs.pop("chart_year", None)
        super().__init__(*args, **kwargs)

        qs = Account.objects.filter(is_active=True, is_postable=True)

        if chart_year:
            qs = qs.filter(chart_year=chart_year)

        # === OUTPUT TAX ACCOUNT (PPN KELUARAN) ===
        self.fields["output_account"].queryset = qs.filter(
            Q(type="liability") &
            (Q(code__startswith="21") | Q(name__icontains="tax"))
        ).order_by("code")

        # === INPUT TAX ACCOUNT (PPN MASUKAN) ===
        self.fields["input_account"].queryset = qs.filter(
            Q(type="asset") &
            (Q(code__startswith="15") | Q(name__icontains="tax"))
        ).order_by("code")