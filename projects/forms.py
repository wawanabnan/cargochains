
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


class ProjectCostForm(forms.ModelForm):
    class Meta:
        model = m.ProjectCost
        fields = ["project", "category", "title", "amount", "currency_code", "cost_date", "notes"]
        widgets = {
            "cost_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),  # BS5
        }

    def __init__(self, *args, **kwargs):
        project_initial = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if not isinstance(f.widget, (forms.CheckboxInput,)):
                f.widget.attrs.setdefault("class", "form-control")
        if project_initial:
            self.fields["project"].initial = project_initial
            self.fields["project"].widget = forms.HiddenInput()
