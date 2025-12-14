from django import forms
from django.utils import timezone
from sales.invoice_model import Invoice
from sales.job_order_model import JobOrder


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "job_order",
            "invoice_date",
            "due_date",
            "subtotal_amount",
            "tax_amount",
            "total_amount",
            "notes_customer",
            "notes_internal",
        ]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes_customer": forms.Textarea(attrs={"rows": 3}),
            "notes_internal": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        qs = JobOrder.objects.select_related("customer").order_by("-id")
        self.fields["job_order"].queryset = qs
        self.fields["job_order"].widget.attrs.update({"class": "form-select"})

        # AdminLTE-friendly styling (aman untuk berbagai widget)
        for name, field in self.fields.items():
            w = field.widget
            css = w.attrs.get("class", "")

            if name == "job_order":
                continue

            if isinstance(w, forms.Select):
                w.attrs["class"] = (css + " form-select").strip()
            elif isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = (css + " form-check-input").strip()
            else:
                w.attrs["class"] = (css + " form-control").strip()

        # Kalau EDIT (instance sudah ada), lock job_order
        if self.instance and self.instance.pk:
            self.fields["job_order"].disabled = True


class InvoiceGenerateForm(forms.Form):
    MODE_FULL = "FULL"
    MODE_CUSTOM = "CUSTOM"
    MODE_CHOICES = [
        (MODE_FULL, "Full amount (total Job Order)"),
        (MODE_CUSTOM, "Custom amount"),
    ]

    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        widget=forms.RadioSelect,
        initial=MODE_FULL,
        label="Invoice Mode",
    )

    invoice_date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Invoice Date",
    )

    due_date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Due Date",
    )

    amount = forms.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        label="Invoice Amount",
        help_text="Untuk mode FULL akan otomatis memakai total Job Order.",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    notes_customer = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        label="Notes to Customer",
    )

    notes_internal = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        label="Internal Notes",
    )

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("mode")
        amount = cleaned.get("amount")

        if mode == self.MODE_CUSTOM:
            if not amount or amount <= 0:
                self.add_error("amount", "Untuk mode Custom, amount wajib diisi dan > 0.")
        return cleaned
