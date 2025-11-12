
from django import forms
from . import models as m


class ProjectForm(forms.ModelForm):
    class Meta:
        model = m.Project
        fields = ["name", "ref_number", "category", "status", "start_date", "end_date", "description"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if not isinstance(f.widget, (forms.CheckboxInput,)):
                f.widget.attrs.setdefault("class", "form-control")


# projects/forms.py
from django import forms
from .models import ProjectCost, Project, CostCategory

class ProjectCostForm(forms.ModelForm):
    class Meta:
        model = ProjectCost
        fields = [
            "project", "category", "title", "amount", "currency_code",
            "cost_date", "ref", "notes", "attachment",
        ]
        widgets = {
            "project": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "category": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "title": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Cost title"}),
            "amount": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01"}),
            "currency_code": forms.TextInput(attrs={"class": "form-control form-control-sm", "maxlength": 3}),
            "cost_date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
            "ref": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Reference"}),
            "notes": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 3}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control form-control-sm"}),
        }

    def clean_currency_code(self):
        ccy = (self.cleaned_data.get("currency_code") or "").upper().strip()
        return ccy or "IDR"
