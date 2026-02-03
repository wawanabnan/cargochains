from django import forms
from django.utils import timezone

from job.models.quotations import Quotation
from core.models.settings import CoreSetting

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
        # ✅ number ikut form supaya bisa di-hide saat create (seperti JobOrderForm) :contentReference[oaicite:0]{index=0}
        fields = ["number", "quote_date", "valid_until"]

    def clean(self):
        cleaned = super().clean()
        qd = cleaned.get("quote_date")
        vu = cleaned.get("valid_until")
        if vu and qd and vu < qd:
            self.add_error("valid_until", "Valid Until tidak boleh lebih kecil dari Quote Date.")
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = getattr(self, "instance", None)
        is_create = not (instance and instance.pk)

        # default quote_date on create GET      
        if is_create and not self.is_bound:
            today = timezone.localdate()

            # 1️⃣ quote_date = hari ini
            self.initial.setdefault("quote_date", today)

            # 2️⃣ valid_until = today + setting
            days = getattr(CoreSetting, "quotation_valid_days", 0) or 0
            if days > 0:
                self.initial.setdefault("valid_until", today + timedelta(days=days))

        
        # number hidden on create + not required + dummy display disabled (mirror JobOrderForm) :contentReference[oaicite:1]{index=1}
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

        # styling massal (biar konsisten dengan JobOrderForm)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select form-select-sm")
            else:
                css = w.attrs.get("class", "")
                if "form-control" not in css:
                    css = "form-control form-control-sm"
                w.attrs["class"] = css
