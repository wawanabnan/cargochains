from django import forms
from accounting.models.chart import Account


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "code",
            "name",
            "type",
            "parent",        # ⬅️ WAJIB
            "is_postable",
            "is_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "parent": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "is_postable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Parent hanya boleh account non-postable (GROUP)
        self.fields["parent"].queryset = Account.objects.filter(is_postable=False)

        # Parent optional
        self.fields["parent"].required = False

class AccountImportForm(forms.Form):
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={"class": "form-control form-control-sm"})
    )
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        label="Overwrite existing (timpa jika code sudah ada)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
