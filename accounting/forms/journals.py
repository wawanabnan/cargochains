from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from accounting.models.journal import Journal, JournalLine
from accounting.models.chart import Account


class JournalForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = [ "date", "ref", "description"]
        widgets = {
        
            "date": forms.DateInput(attrs={"class": "form-control form-control-sm", "type": "date"}),
            "ref": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "description": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 2}),
        }


class JournalLineForm(forms.ModelForm):
    account_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    account_text = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm js-acct-text",
            "autocomplete": "off",
            "placeholder": "Ketik: 1101 Cash...",
        })
    )

    class Meta:
        model = JournalLine
        fields = ["label", "debit", "credit"]
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "debit": forms.NumberInput(attrs={"class": "form-control form-control-sm text-end", "step": "0.01"}),
            "credit": forms.NumberInput(attrs={"class": "form-control form-control-sm text-end", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # kalau edit existing line → isi text & hidden
        if self.instance and self.instance.pk and self.instance.account_id:
            acc = self.instance.account
            self.fields["account_id"].initial = acc.id
            self.fields["account_text"].initial = f"{acc.code} - {acc.name}"

        self.fields["debit"].required = False
        self.fields["credit"].required = False

    def clean(self):
        cleaned = super().clean()
        acct_id = cleaned.get("account_id")

        if acct_id:
            acc = Account.objects.get(pk=acct_id)
            if not acc.is_postable:
                raise ValidationError("Tidak boleh posting ke parent/group account.")


        # Skip empty row (biar user bisa add row terus delete)
        debit = cleaned.get("debit") or 0
        credit = cleaned.get("credit") or 0
        txt = (cleaned.get("account_text") or "").strip()

        if not acct_id and not txt and not debit and not credit:
            return cleaned

        if not acct_id:
            raise ValidationError("Account wajib dipilih dari autocomplete.")

        # validasi debit/credit
        if debit and credit:
            raise ValidationError("Line tidak boleh debit dan credit sekaligus.")
        if debit < 0 or credit < 0:
            raise ValidationError("Debit/Credit tidak boleh minus.")

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        acct_id = self.cleaned_data.get("account_id")
        if acct_id:
            obj.account = Account.objects.get(pk=acct_id)
        if commit:
            obj.save()
            self.save_m2m()
        return obj


JournalLineFormSet = inlineformset_factory(
    Journal,
    JournalLine,
    form=JournalLineForm,
    fields=["account", "label", "debit", "credit"],
    extra=2,
    can_delete=True,
)
