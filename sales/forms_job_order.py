from decimal import Decimal, InvalidOperation

from django import forms

from .job_order_model import JobOrder
from partners.models import Partner


class JobOrderForm(forms.ModelForm):
    class Meta:
        model = JobOrder
        fields = "__all__"
        # sales_user, is_pph, pph_amount tidak tampil
        exclude = ["created", "modified", "is_pph", "pph_amount", "sales_user"]

        widgets = {
            "job_date": forms.DateInput(attrs={"type": "date"}),

            "service": forms.Select(),
            "customer": forms.Select(),
            "cargo_description": forms.TextInput(),
            "quantity": forms.NumberInput(attrs={"step": "0.01"}),

            "pickup": forms.TextInput(),
            "delivery": forms.TextInput(),
            "pic": forms.TextInput(),

            "payment_term": forms.Select(),
            "currency": forms.Select(),

            "remarks_internal": forms.Textarea(attrs={"rows": 3}),

            # TAX
            "is_tax": forms.CheckboxInput(),
            # pakai TextInput supaya bisa format Indonesia 1.000.000,00
            "total_amount": forms.TextInput(),
            "tax_amount": forms.TextInput(attrs={"readonly": "readonly", "tabindex": "-1"}),
            "grand_total": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter customer hanya role customer (kalau struktur roles mendukung)
      
        # Styling massal
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select form-select-sm")
            else:
                # angka rata kanan biar enak lihat
                extra = " text-end" if name in ("total_amount", "tax_amount", "grand_total") else ""
                widget.attrs.setdefault("class", f"form-control form-control-sm{extra}")

        # default 0 untuk form baru
        if not self.instance.pk and not self.is_bound:
            self.initial.setdefault("total_amount", "0,00")
            self.initial.setdefault("tax_amount", "0,00")
            self.initial.setdefault("grand_total", "0,00")

    # --- helper parse & format angka Indonesia ---
    def _parse_id_decimal(self, value_str):
        """
        Ubah string format Indonesia '1.000.000,00' jadi Decimal('1000000.00')
        """
        if value_str in (None, ""):
            return Decimal("0")
        s = str(value_str).strip()
        # hapus spasi
        s = s.replace(" ", "")
        # hilangkan pemisah ribuan titik, koma jadi titik desimal
        s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except InvalidOperation:
            raise forms.ValidationError("Format angka tidak valid. Gunakan contoh: 1.000,00")

from decimal import Decimal, InvalidOperation

from django import forms

from .job_order_model import JobOrder
from partners.models import Customer   # atau Partner kalau FK-nya masih ke Partner


class JobOrderForm(forms.ModelForm):
    # OVERRIDE: field angka jadi CharField supaya boleh format "1.000,00"
    total_amount = forms.CharField(required=False)
    tax_amount = forms.CharField(required=False)
    grand_total = forms.CharField(required=False)

    class Meta:
        model = JobOrder
        fields = "__all__"
        exclude = ["created", "modified", "is_pph", "pph_amount", "sales_user"]

        widgets = {
            "job_date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),

            "service": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "customer": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "cargo_description": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01"}),
            "pickup": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "delivery": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "pic": forms.TextInput(attrs={"class": "form-control form-control-sm"}),

            "payment_term": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "currency": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "remarks_internal": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 3}),

            "is_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            # angka: text + rata kanan
            "total_amount": forms.TextInput(attrs={"class": "form-control form-control-sm text-end"}),
            "tax_amount": forms.TextInput(attrs={
                "class": "form-control form-control-sm text-end",
                "readonly": "readonly",
                "tabindex": "-1",
            }),
            "grand_total": forms.TextInput(attrs={"class": "form-control form-control-sm text-end"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # styling massal (selain yang sudah di Meta.widgets)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select form-select-sm")
            else:
                if "form-control" not in widget.attrs.get("class", ""):
                    widget.attrs.setdefault("class", "form-control form-control-sm")

        # default angka 0,00 untuk form baru
        if not self.instance.pk and not self.is_bound:
            self.initial.setdefault("total_amount", "0,00")
            self.initial.setdefault("tax_amount", "0,00")
            self.initial.setdefault("grand_total", "0,00")

    # ============== helper angka Indonesia ==============

    def _parse_id_decimal(self, value_str, field_label="angka"):
        """
        Ubah string format Indonesia '1.000.000,00' -> Decimal('1000000.00')
        """
        if value_str in (None, ""):
            return Decimal("0")
        s = str(value_str).strip()
        s = s.replace(" ", "")
        s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except InvalidOperation:
            raise forms.ValidationError(
                f"Format {field_label} tidak valid. Gunakan contoh: 1.000,00"
            )

    # ============== clean utama ==============

    def clean(self):
        cleaned = super().clean()

        # string mentah dari field Form (CharField)
        total_raw = cleaned.get("total_amount") or ""
        is_tax = cleaned.get("is_tax") or False

        # parse total ke Decimal
        total = self._parse_id_decimal(total_raw, field_label="Total Amount")

        # hitung tax 1.1% kalau dicentang
        if is_tax:
            tax = (total * Decimal("0.011")).quantize(Decimal("0.01"))
        else:
            tax = Decimal("0.00")

        grand = (total + tax).quantize(Decimal("0.01"))

        # masukkan kembali ke cleaned_data sebagai Decimal
        cleaned["total_amount"] = total
        cleaned["tax_amount"] = tax
        cleaned["grand_total"] = grand

        return cleaned
