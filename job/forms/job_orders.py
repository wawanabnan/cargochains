from decimal import Decimal, InvalidOperation
from django import forms
from job.models.job_orders import JobOrder
from partners.models import Customer  # proxy Customer yang sudah om buat
from django.urls import reverse_lazy
from geo.models import Location
from core.services.customer_notes import get_customer_notes

PPH_RATE = Decimal("0.02")  # 2% dari DPP (total_amount)


class JobOrderForm(forms.ModelForm):
    # Override field angka supaya bisa pakai format "1.000,00"
    qty = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm text-end"})
    )
    price = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm text-end"})
    )

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
            "origin": forms.Select(attrs={
                "class": "form-control js-location-select",
                "data-placeholder": "Pilih origin",
                "data-url": reverse_lazy("geo:locations_select2"),
            }),
            "destination": forms.Select(attrs={
                "class": "form-control js-location-select",
                "data-placeholder": "Pilih destination",
                "data-url": reverse_lazy("geo:locations_select2"),
            }),
            "cargo_description": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "cargo_dimension": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "customer_note": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "sla_note": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),

            "pickup": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "delivery": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "shipper_name": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "step": "0.01"}
            ),
           
            "consignee_name": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "step": "0.01"}
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

        defaults = get_customer_notes()
        instance = getattr(self, "instance", None)

        def _empty(v):
            return not (v or "").strip()

        # =========================
        # SALES DEFAULT NOTES (safe)
        # =========================

        # CREATE: form baru (GET) → isi initial dari CoreSetting
        if not instance.pk and not self.is_bound:
            if "customer_note" in self.fields and _empty(self.initial.get("customer_note", "")):
                self.initial["customer_note"] = defaults.get("customer_note", "") or ""
            if "sla_note" in self.fields and _empty(self.initial.get("sla_note", "")):
                self.initial["sla_note"] = defaults.get("sla_note", "") or ""

        # UPDATE: edit (GET) → isi initial hanya kalau instance masih kosong
        if instance.pk and not self.is_bound:
            if "customer_note" in self.fields and _empty(getattr(instance, "customer_note", "")):
                self.initial["customer_note"] = defaults.get("customer_note", "") or ""
            if "sla_note" in self.fields and _empty(getattr(instance, "sla_note", "")):
                self.initial["sla_note"] = defaults.get("sla_note", "") or ""



        self.fields["origin"].queryset = Location.objects.none()
        self.fields["destination"].queryset = Location.objects.none()

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
                if name in ("total_amount", "tax_amount", "grand_total", "pph_amount", "kurs_idr", "total_in_idr","qty","price"):
                    if "text-end" not in css:
                        css += " text-end"
                widget.attrs["class"] = css

        
        # default angka untuk form baru
        if not self.instance.pk and not self.is_bound:
            self.initial.setdefault("qty", "0,00")
            self.initial.setdefault("price", "0,00")
            self.initial.setdefault("total_amount", "0,00")
            self.initial.setdefault("tax_amount", "0,00")
            self.initial.setdefault("grand_total", "0,00")
            self.initial.setdefault("pph_amount", "0,00")
            self.initial.setdefault("kurs_idr", "1,00")

        # total_amount read-only (tetap ikut submit)
        if "total_amount" in self.fields:
            self.fields["total_amount"].widget.attrs["readonly"] = True
            self.fields["total_amount"].help_text = "Otomatis: qty × price"



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

        # ----- QTY / PRICE / TOTAL -----
        qty_raw = cleaned.get("qty") or ""
        price_raw = cleaned.get("price") or ""

        qty = self._parse_id_decimal(qty_raw, "Qty") if isinstance(qty_raw, str) else (qty_raw or Decimal("0"))
        price = self._parse_id_decimal(price_raw, "Price") if isinstance(price_raw, str) else (price_raw or Decimal("0"))

        if qty < 0:
            self.add_error("qty", "Qty tidak boleh negatif.")
        if price < 0:
            self.add_error("price", "Price tidak boleh negatif.")

        total = (qty * price).quantize(Decimal("0.01"))
        cleaned["qty"] = qty
        cleaned["price"] = price
        cleaned["total_amount"] = total  # selalu override

        # ----- TAXES dari MASTER TAX -----
        tax_amount = Decimal("0.00")
        pph_amount = Decimal("0.00")

        taxes = cleaned.get("taxes")  # biasanya queryset/list tax objects
        if taxes:
            for t in taxes:
                # 1) kalau master tax punya rumus sendiri
                if hasattr(t, "calculate") and callable(getattr(t, "calculate")):
                    amt = t.calculate(total)
                    amt = amt if isinstance(amt, Decimal) else Decimal(str(amt or "0"))
                else:
                    # 2) fallback: pakai rate (kalau memang ada)
                    # dukung beberapa naming umum: rate, rate_percent
                    rate = None
                    if hasattr(t, "rate") and t.rate is not None:
                        rate = Decimal(str(t.rate))
                    elif hasattr(t, "rate_percent") and t.rate_percent is not None:
                        rate = Decimal(str(t.rate_percent)) / Decimal("100")
                    else:
                        rate = Decimal("0")

                    amt = (total * rate).quantize(Decimal("0.01"))

                # klasifikasi: withholding/pph vs tax penambah
                # dukung flag umum: is_withholding, is_pph, kind/code/category
                is_withholding = False
                if hasattr(t, "is_withholding"):
                    is_withholding = bool(t.is_withholding)
                elif hasattr(t, "is_pph"):
                    is_withholding = bool(t.is_pph)
                elif hasattr(t, "code"):
                    is_withholding = (str(t.code).lower() == "pph")
                elif hasattr(t, "kind"):
                    is_withholding = (str(t.kind).lower() == "pph")

                if is_withholding:
                    pph_amount += amt
                else:
                    tax_amount += amt

        tax_amount = tax_amount.quantize(Decimal("0.01"))
        pph_amount = pph_amount.quantize(Decimal("0.01"))
        grand = (total + tax_amount - pph_amount).quantize(Decimal("0.01"))

        cleaned["tax_amount"] = tax_amount
        cleaned["pph_amount"] = pph_amount
        cleaned["grand_total"] = grand

        # ----- KURS -----
        currency = cleaned.get("currency")
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
