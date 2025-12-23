# sales/forms_job_order.py
from decimal import Decimal, InvalidOperation

from django import forms

from ..job_order_model import JobOrder
from partners.models import Customer  # proxy Customer yang sudah om buat

PPH_RATE = Decimal("0.02")  # 2% dari DPP (total_amount)


class JobOrderForm2(forms.ModelForm):
    # Override field angka supaya bisa pakai format "1.000,00"
    total_amount = forms.CharField(required=False)
    tax_amount = forms.CharField(required=False)
    grand_total = forms.CharField(required=False)

    # PPH dihitung otomatis, tapi tetap kita definisikan supaya bisa ditampilkan
    pph_amount = forms.CharField(required=False, label="PPH Amount")

    job_date = forms.DateField(
        label="Job Date",
        input_formats=["%d-%m-%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm js-jobdate",
                "autocomplete": "off",
                "placeholder": "dd-mm-yyyy",
            }
        ),
    )

    class Meta:
        model = JobOrder
        fields = "__all__"
        exclude = [
            "number",       # auto pakai get_next_number di model
            "created",
            "modified",
            "sales_user",
            "total_in_idr",
            "status"
        ]

        widgets = {
            "service": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "customer": forms.Select(attrs={"class": "form-select form-select-sm"}),

            
            "cargo_description": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),

            "pickup": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "delivery": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),

            "quantity": forms.NumberInput(
                attrs={"class": "form-control form-control-sm", "step": "0.01"}
            ),
            "pic": forms.TextInput(attrs={"class": "form-control form-control-sm"}),

            "payment_term": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "currency": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "remarks_internal": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 3}
            ),

            "is_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_pph": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            # angka: text-end + readonly di tax & pph
            "total_amount": forms.TextInput(
                attrs={"class": "form-control form-control-sm text-end"}
            ),
            "tax_amount": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm text-end",
                    "readonly": "readonly",
                    "tabindex": "-1",
                }
            ),
            "pph_amount": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm text-end",
                    "readonly": "readonly",
                    "tabindex": "-1",
                }
            ),
            "grand_total": forms.TextInput(
                attrs={"class": "form-control form-control-sm text-end"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # dropdown customer → proxy Customer (cuma yang punya role customer)
        if "customer" in self.fields:
            self.fields["customer"].queryset = Customer.objects.all().order_by("name")

       
        # kurs_idr: di create jangan required, default 1,00
        if "kurs_idr" in self.fields:
            self.fields["kurs_idr"].required = False
            self.fields["kurs_idr"].widget.attrs.setdefault("class", "form-control form-control-sm text-end")
            self.fields["kurs_idr"].widget.attrs.setdefault("inputmode", "decimal")
            if not self.instance.pk and not self.is_bound:
                self.initial.setdefault("kurs_idr", "1,00")
     

        # styling massal (jaga-jaga kalau ada field tambahan)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select form-select-sm")
            else:
                css = widget.attrs.get("class", "")
                if "form-control" not in css:
                    css = "form-control form-control-sm"
                    if name in (
                        "total_amount",
                        "tax_amount",
                        "grand_total",
                        "pph_amount",
                        "kurs_idr",
                        "total_in_idr",
                    ):
                        css += " text-end"
                    widget.attrs["class"] = css


        # default angka untuk form baru
        if not self.instance.pk and not self.is_bound:
            self.initial.setdefault("total_amount", "0,00")
            self.initial.setdefault("tax_amount", "0,00")
            self.initial.setdefault("grand_total", "0,00")
            self.initial.setdefault("pph_amount", "0,00")
            # kalau pakai kurs:
            # self.initial.setdefault("curs_idr", "1,00")
            # self.initial.setdefault("total_in_idr", "0,00")

    # ========== helper parse angka Indonesia ==========
    def _parse_id_decimal(self, value_str, field_label="angka"):
        """
        '1.000.000,00' -> Decimal('1000000.00')
        """
        if value_str in (None, ""):
            return Decimal("0")
        s = str(value_str).strip()
        s = s.replace(" ", "")
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except InvalidOperation:
            raise forms.ValidationError(
                f"Format {field_label} tidak valid. Gunakan contoh: 1.000,00"
            )

    # ========== clean utama ==========
    def clean(self):
        cleaned = super().clean()

        # ----- TOTAL / TAX / GRAND -----
        total_raw = cleaned.get("total_amount") or ""
        is_tax = cleaned.get("is_tax") or False
        is_pph = cleaned.get("is_pph") or False

        total = self._parse_id_decimal(total_raw, "Total Amount")

        # Tax 1.1% kalau dicentang
        if is_tax:
            tax = (total * Decimal("0.011")).quantize(Decimal("0.01"))
        else:
            tax = Decimal("0.00")

        if is_pph:
            pph = (total * PPH_RATE).quantize(Decimal("0.01"))
        else:
            pph = Decimal("0.00")    

        grand = (total + tax - pph).quantize(Decimal("0.01"))

        cleaned["total_amount"] = total
        cleaned["tax_amount"] = tax
        cleaned["pph_amount"] = pph
        cleaned["grand_total"] = grand


        # (kalau om punya logic kurs & total_in_idr, bisa lanjut di bawah sini)
        currency = cleaned.get("currency")  # FK object atau None
        code = (currency.code or "").upper() if currency else ""

        if code == "IDR":
            # IDR: kurs tidak perlu diisi, paksa 1.00
            cleaned["kurs_idr"] = Decimal("1.00")
            # optional: kalau user terlanjur isi, tetap override ke 1.00
        else:
            kurs = cleaned.get("kurs_idr")

            if kurs in (None, ""):
                self.add_error("kurs_idr", "Kurs wajib diisi untuk currency selain IDR.")
            else:
                # kalau kurs_idr di form masih TextInput string, parse indo dulu
                if isinstance(kurs, str):
                    kurs = self._parse_id_decimal(kurs, "Kurs")
                if kurs is not None and kurs <= 0:
                    self.add_error("kurs_idr", "Kurs harus lebih besar dari 0.")
                cleaned["kurs_idr"] = kurs

        return cleaned

class JobOrderForm(forms.ModelForm):
    # Override field angka supaya bisa pakai format "1.000,00"
    total_amount = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm text-end"})
    )
    tax_amount = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm text-end",
            "readonly": "readonly",
            "tabindex": "-1",
        })
    )
    grand_total = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm text-end"})
    )

    # PPH dihitung otomatis, tapi tetap kita definisikan supaya bisa ditampilkan
    pph_amount = forms.CharField(
        required=False,
        label="PPH Amount",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm text-end",
            "readonly": "readonly",
            "tabindex": "-1",
        })
    )

    # ✅ FIX UTAMA: override kurs_idr agar bisa input "1,00" / "15.000,00"
    kurs_idr = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm text-end",
            "inputmode": "decimal",
        })
    )

    job_date = forms.DateField(
        label="Job Date",
        input_formats=["%d-%m-%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm js-jobdate",
                "autocomplete": "off",
                "placeholder": "dd-mm-yyyy",
            }
        ),
    )

    class Meta:
        model = JobOrder
        fields = "__all__"
        exclude = [
            "number",
            "created",
            "modified",
            "sales_user",
            "total_in_idr",
            "status",
        ]
        widgets = {
            "service": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "customer": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "cargo_description": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "pickup": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "delivery": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),

            "quantity": forms.NumberInput(
                attrs={"class": "form-control form-control-sm", "step": "0.01"}
            ),
            "pic": forms.TextInput(attrs={"class": "form-control form-control-sm"}),

            "payment_term": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "currency": forms.Select(attrs={"class": "form-select form-select-sm"}),

            "remarks_internal": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 3}
            ),

            "is_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_pph": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            # ⚠️ jangan taruh widget utk total/tax/pph/grand/kurs di sini
            # karena field-field tsb sudah dioverride di atas.
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # dropdown customer → proxy Customer (cuma yang punya role customer)
        if "customer" in self.fields:
            self.fields["customer"].queryset = Customer.objects.all().order_by("name")

        # styling massal (jaga-jaga kalau ada field tambahan)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select form-select-sm")
            else:
                css = widget.attrs.get("class", "")
                if "form-control" not in css:
                    css = "form-control form-control-sm"
                if name in ("total_amount", "tax_amount", "grand_total", "pph_amount", "kurs_idr", "total_in_idr"):
                    if "text-end" not in css:
                        css += " text-end"
                widget.attrs["class"] = css

        # default angka untuk form baru
        if not self.instance.pk and not self.is_bound:
            self.initial.setdefault("total_amount", "0,00")
            self.initial.setdefault("tax_amount", "0,00")
            self.initial.setdefault("grand_total", "0,00")
            self.initial.setdefault("pph_amount", "0,00")
            self.initial.setdefault("kurs_idr", "1,00")

    # ========== helper parse angka Indonesia ==========
    def _parse_id_decimal(self, value_str, field_label="angka"):
        """
        '1.000.000,00' -> Decimal('1000000.00')
        """
        if value_str in (None, ""):
            return Decimal("0")
        s = str(value_str).strip()
        s = s.replace(" ", "")
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except InvalidOperation:
            raise forms.ValidationError(
                f"Format {field_label} tidak valid. Gunakan contoh: 1.000,00"
            )

    # ========== clean utama ==========
    def clean(self):
        cleaned = super().clean()

        # ----- TOTAL / TAX / PPH / GRAND -----
        total_raw = cleaned.get("total_amount") or ""
        is_tax = cleaned.get("is_tax") or False
        is_pph = cleaned.get("is_pph") or False

        total = self._parse_id_decimal(total_raw, "Total Amount")

        tax = (total * Decimal("0.011")).quantize(Decimal("0.01")) if is_tax else Decimal("0.00")
        pph = (total * PPH_RATE).quantize(Decimal("0.01")) if is_pph else Decimal("0.00")
        grand = (total + tax - pph).quantize(Decimal("0.01"))

        cleaned["total_amount"] = total
        cleaned["tax_amount"] = tax
        cleaned["pph_amount"] = pph
        cleaned["grand_total"] = grand

        # ----- KURS -----
        currency = cleaned.get("currency")  # FK object atau None
        code = (currency.code or "").upper() if currency else ""

        if code == "IDR":
            cleaned["kurs_idr"] = Decimal("1.00")
        else:
            kurs_raw = cleaned.get("kurs_idr")
            if kurs_raw in (None, ""):
                self.add_error("kurs_idr", "Kurs wajib diisi untuk currency selain IDR.")
            else:
                kurs = self._parse_id_decimal(kurs_raw, "Kurs") if isinstance(kurs_raw, str) else kurs_raw
                if kurs is not None and kurs <= 0:
                    self.add_error("kurs_idr", "Kurs harus lebih besar dari 0.")
                cleaned["kurs_idr"] = kurs

        return cleaned
