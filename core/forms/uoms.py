# core/forms/uoms.py

from django import forms
from core.models.uoms import UOM

UOM_CATEGORY_CHOICES = [
    ("weight", "Weight"),
    ("volume", "Volume"),
    ("length", "Length"),
    ("count", "Count"),
    ("time", "Time"),
    ("service", "Service / Lump Sum"),
]

class UOMForm(forms.ModelForm):
    category = forms.ChoiceField(
        choices=UOM_CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = UOM
        fields = ["code", "name", "category", "is_active"]

        widgets = {
            "code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "KG / CBM / PCS"
            }),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Kilogram / Cubic Meter"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }
