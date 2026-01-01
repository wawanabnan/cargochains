from django import forms
from core.models.services import Service
from accounting.models.chart import Account


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            "name",
            "service_group",
            "revenue_account",
            "receivable_account",
            "sort_order",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "service_group": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "revenue_account": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "receivable_account": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control form-control-sm text-end"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔹 Revenue → hanya Income
        self.fields["revenue_account"].queryset = Account.objects.filter(
            is_active=True,
            is_postable=True,
            type="income",
        ).order_by("code")

        # 🔹 Receivable (AR) → Asset saja
        self.fields["receivable_account"].queryset = Account.objects.filter(
            is_active=True,
            is_postable=True,
            type="asset",
        ).order_by("code")
