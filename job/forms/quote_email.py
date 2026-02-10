from django import forms

class QuotationEmailForm(forms.Form):
    to = forms.CharField(
        label="To",
        help_text="Pisahkan dengan koma jika lebih dari satu.",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "email@client.com"}),
    )
    cc = forms.CharField(
        label="CC",
        required=False,
        help_text="Opsional, pisahkan dengan koma.",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "cc@company.com"}),
    )
    subject = forms.CharField(
        label="Subject",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    message = forms.CharField(
        label="Message",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 8}),
    )
    attach_pdf = forms.BooleanField(
        label="Attach PDF Quotation",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_to(self):
        return self._clean_emails(self.cleaned_data["to"], field="to")

    def clean_cc(self):
        val = (self.cleaned_data.get("cc") or "").strip()
        if not val:
            return []
        return self._clean_emails(val, field="cc")

    def _clean_emails(self, raw, field="to"):
        emails = [e.strip() for e in raw.split(",") if e.strip()]
        if not emails:
            raise forms.ValidationError("Email tujuan wajib diisi.")
        # validasi email sederhana via EmailField
        ef = forms.EmailField()
        bad = []
        ok = []
        for e in emails:
            try:
                ef.clean(e)
                ok.append(e)
            except forms.ValidationError:
                bad.append(e)
        if bad:
            raise forms.ValidationError(f"Email tidak valid: {', '.join(bad)}")
        return ok
