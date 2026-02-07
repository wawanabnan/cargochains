from django import forms
from django.utils import timezone

from job.models.quotations import Quotation
from core.models.settings import CoreSetting
from datetime import timedelta


class QuotationForm(forms.ModelForm):
    
    quote_date = forms.DateField(
        label="Quotation Date",
        input_formats=["%d-%m-%Y", "%Y-%m-%d"],
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm js-date",
            "autocomplete": "off",
            "placeholder": "dd-mm-yyyy",
        }),
    )

    valid_until = forms.DateField(
        label="Valid Until",
        required=False,
        input_formats=["%d-%m-%Y", "%Y-%m-%d"],
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm js-date",
            "autocomplete": "off",
            "placeholder": "dd-mm-yyyy",
        }),
    )

    class Meta:
        model = Quotation
        fields = ["number", "quote_date", "valid_until"]

    def clean(self):
        cleaned = super().clean()
        qd = cleaned.get("quote_date")
        vu = cleaned.get("valid_until")
        if vu and qd and vu < qd:
            self.add_error("valid_until", "Valid Until tidak boleh lebih kecil dari Quote Date.")
        return cleaned

    @staticmethod
    def get_valid_days() -> int:
        row = (
            CoreSetting.objects
            .filter(code__iexact="QUOTATION_VALID_DAY")
            .only("int_value")
            .first()
        )
        if not row or row.int_value is None:
            return 0
        return int(row.int_value)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = getattr(self, "instance", None)
        is_create = not (instance and instance.pk)

        # default hanya untuk create GET (bukan POST)
        if is_create and not self.is_bound:
            today = timezone.localdate()
            self.initial.setdefault("quote_date", today)

            days = self.get_valid_days()
            if days > 0:
                qd = self.initial.get("quote_date") or today
                self.initial.setdefault("valid_until", qd + timedelta(days=days))

        # number hidden on create + dummy disabled (mirip JobOrderForm)
        if "number" in self.fields and is_create:
            self.fields["number"].required = False
            self.fields["number"].widget = forms.HiddenInput()
            self.fields["number_display"] = forms.CharField(
                label=self.fields["number"].label or "Quotation #",
                required=False,
                initial="(auto)",
                disabled=True,
                widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            )

        # styling massal (TIDAK menghapus class yang sudah ada seperti js-date)
        for name, field in self.fields.items():
            w = field.widget

            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
                continue

            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select form-select-sm")
                continue

            # input/textarea/etc
            css = w.attrs.get("class", "")
            if "form-control" not in css:
                css = (css + " form-control form-control-sm").strip()
            w.attrs["class"] = css

        print("is_bound:", self.is_bound)
        print("initial quote_date:", self.initial.get("quote_date"))
        days = self.get_valid_days()
        print("VALID DAYS =", days)