from django import forms
from django.utils import timezone

from core.models.number_sequences import NumberSequence  # sesuaikan path

class NumberSequenceForm(forms.ModelForm):
    preview = forms.CharField(
        required=False,
        label="Preview",
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": True}),
        help_text="Contoh hasil berdasarkan format saat ini (simulasi).",
    )

    class Meta:
        model = NumberSequence
        fields = [
            "app_label", "code", "name",
            "prefix", "format", "padding", "reset",
            "last_number", "period_year", "period_month",
        ]
        widgets = {
            "app_label": forms.TextInput(attrs={"class": "form-control", "placeholder": ""}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": ""}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": ""}),
            "prefix": forms.TextInput(attrs={"class": "form-control", "placeholder": ""}),
            "format": forms.TextInput(attrs={"class": "form-control"}),
            "padding": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),

            "reset": forms.Select(attrs={"class": "form-select"}),

            "last_number": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "period_year": forms.NumberInput(attrs={"class": "form-control", "min": "2000", "max": "2100"}),
            "period_month": forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "12"}),
        }

    def clean_format(self):
        fmt = (self.cleaned_data.get("format") or "").strip()
        if not fmt:
            raise forms.ValidationError("Format wajib diisi.")

        # Cek variabel yang diizinkan (strict, biar user ga bikin format aneh)
        allowed = {"prefix", "year", "month", "day", "seq"}
        # parsing sederhana: cari {var...}
        import re
        for m in re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)[^}]*\}", fmt):
            if m not in allowed:
                raise forms.ValidationError(
                    f"Variabel '{{{m}}}' tidak dikenali. Yang boleh: prefix, year, month, day, seq."
                )

        # Coba render simulasi (kalau error format string, stop di sini)
        now = timezone.localdate()
        sample = {
            "prefix": self.cleaned_data.get("prefix") or "",
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "seq": 1,
        }
        try:
            fmt.format(**sample)
        except Exception as e:
            raise forms.ValidationError(f"Format tidak valid: {e}")

        return fmt

    def clean(self):
        cleaned = super().clean()

        # Set preview
        try:
            now = timezone.localdate()
            seq_next = (cleaned.get("last_number") or 0) + 1
            fmt = cleaned.get("format") or ""
            prefix = cleaned.get("prefix") or ""
            sample = {
                "prefix": prefix,
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "seq": seq_next,
            }
            cleaned["preview"] = fmt.format(**sample)
        except Exception:
            cleaned["preview"] = ""

        return cleaned
