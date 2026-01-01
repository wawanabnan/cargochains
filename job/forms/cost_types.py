from django import forms
from django.db.models import Q

from job.models.job_costs import JobCostType
from accounting.models.chart import Account

# TODO: ganti ke service active fiscal year om (Accounting Settings)
def get_active_chart_year(request):
    # sementara: return None kalau belum ada settings
    return getattr(request, "active_chart_year", None)

class JobCostTypeForm(forms.ModelForm):
    class Meta:
        model = JobCostType
        fields = [
            "code",
            "name",
            "cost_group",        # ✅ dulu: group
            "requires_vendor",   # ✅ boolean baru
            "sort_order",
            "is_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "cost_group": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "trucking/freight/port/internal"}),
            "requires_vendor": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
