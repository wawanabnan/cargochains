from decimal import Decimal, InvalidOperation
from django import forms
from django.urls import reverse_lazy
from django.utils import timezone

from job.models.job_orders import JobOrder
from partners.models import Customer
from geo.models import Location
from core.models.taxes import Tax
from sales.services.config import get_sales_defaults

class JobOrderForm(forms.ModelForm):
    taxes = forms.ModelMultipleChoiceField(
        queryset=Tax.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={
            "class": "vb-taxes",
            "multiple": "multiple",
        })
    )
    
    qty = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm text-end"})
    )
    price = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm text-end"})
    )
    discount_value = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm text-end",
        })
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
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm js-jobdate",
            "autocomplete": "off",
            "placeholder": "dd-mm-yyyy",
        }),
    )

    shp_date = forms.DateField(
        label="Job Date",
        input_formats=["%d-%m-%Y", "%Y-%m-%d"],
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm js-jobdate",
            "autocomplete": "off",
            "placeholder": "dd-mm-yyyy",
        }),
    )

    
    class Meta:
        model = JobOrder
        fields = "__all__"
        exclude = ["created", "modified", "sales_user", "total_in_idr", "status","sla_note","pph_amount"]
        widgets = {
            "service": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "job_source": forms.Select(attrs={"class": "form-select form-select-sm"}),
            
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

            "cargo_description": forms.Textarea(attrs={
                "rows": 4,
                "style": "min-height:auto;",
            }),
             "cargo_dimension": forms.Textarea(attrs={
                "rows": 4,
                "style": "min-height:auto;",
            }),
             "pickup": forms.Textarea(attrs={
                "rows": 5,
                "style": "min-height:auto;",
            }),
             "delivery": forms.Textarea(attrs={
                "rows": 5,
                "style": "min-height:auto;",
            }),

            "discount_type": forms.HiddenInput(),
            "discount_value": forms.TextInput(attrs={
                "class": "form-control form-control-sm text-end",
            }),

            "customer_note": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 4}),
            "term_conditions": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 4}),
            "payment_term": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "currency": forms.Select(attrs={"class": "form-select form-select-sm"}),
           # "remarks_internal": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 3}),
            "is_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            

        }

    # ---------- helper ----------
    def _fmt_id(self, val):
        if val is None or val == "":
            return ""
        d = Decimal(str(val))
        s = f"{d:,.2f}"  # 1,234.56
        return s.replace(",", "_").replace(".", ",").replace("_", ".")

    def _parse_id_decimal(self, value_str, field_label="angka"):
        if value_str in (None, ""):
            return Decimal("0")
        s = str(value_str).strip().replace(" ", "")
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except InvalidOperation:
            raise forms.ValidationError(f"Format {field_label} tidak valid. Gunakan contoh: 1.000,00")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        print("RAW POST DP:", self.data.get("down_payment_percent"))
        print("INSTANCE DP:", getattr(self.instance, "down_payment_percent", None))
        print("INITIAL DP:", self.initial.get("down_payment_percent"))
        print("FIELD INITIAL DP:", self.fields.get("down_payment_percent").initial if "down_payment_percent" in self.fields else None)


        if not self.instance.pk:
            self.fields["discount_value"].initial = 0

        instance = getattr(self, "instance", None)
        is_create = not (instance and instance.pk)
        is_edit = bool(instance and instance.pk)

        defaults =get_sales_defaults(target="job_order")

        # service dropdown tampil name aja
        if "service" in self.fields:
            self.fields["service"].label_from_instance = lambda obj: obj.name

        # customer queryset
        if "customer" in self.fields:
            self.fields["customer"].queryset = Customer.objects.all().order_by("name")

        # number hidden on create + not required
        if "number" in self.fields and is_create:
            self.fields["number"].required = False
            self.fields["number"].widget = forms.HiddenInput()
            self.fields["number_display"] = forms.CharField(
                label=self.fields["number"].label or "Job #",
                required=False,
                initial="(auto)",
                disabled=True,
                widget=forms.TextInput(attrs={"class": "form-control form-control-sm"})
            )

        # default job_date on create GET
        if is_create and not self.is_bound:
            self.initial.setdefault("job_date", timezone.now().date())
            self.initial.setdefault("shp_date", timezone.now().date())
           

        # ===== NOTES DEFAULT (tanpa truncate 255 karena sudah TextField) =====
        def _empty(v): return not (v or "").strip()

        if not self.is_bound:
            if is_create:
                if "customer_note" in self.fields and _empty(self.initial.get("customer_note", "")):
                    self.initial["customer_note"] = defaults.get("customer_note", "") or ""
                if "term_conditions" in self.fields and _empty(self.initial.get("term_conditions", "")):
                    self.initial["term_conditions"] = defaults.get("term_conditions", "") or ""
                if "bank_transfer_info" in self.fields and _empty(self.initial.get("bank_transfer_info", "")):
                    self.initial["bank_transfer_info"] = defaults.get("bank_transfer_info", "") or ""
            else:
                if "customer_note" in self.fields and _empty(getattr(instance, "customer_note", "")):
                    self.initial["customer_note"] = defaults.get("customer_note", "") or ""
                if "term_conditions" in self.fields and _empty(getattr(instance, "term_conditions", "")):
                    self.initial["term_conditions"] = defaults.get("term_conditions", "") or ""
                if "bank_transfer_info" in self.fields and _empty(getattr(instance, "bank_transfer_info", "")):
                    self.initial["bank_transfer_info"] = defaults.get("bank_transfer_info", "") or ""


        # ===== EDIT GET: format angka agar tampil indo =====
        if is_edit and not self.is_bound:
            self.initial["price"] = self._fmt_id(getattr(instance, "price", 0) or 0)
            self.initial["qty"] = self._fmt_id(getattr(instance, "qty", 0) or 0)
            self.initial["kurs_idr"] = self._fmt_id(getattr(instance, "kurs_idr", 1) or 1)

            # ini yang kemarin bikin kosong di edit:
            self.initial["total_amount"] = self._fmt_id(getattr(instance, "total_amount", 0) or 0)
            self.initial["tax_amount"] = self._fmt_id(getattr(instance, "tax_amount", 0) or 0)
            self.initial["grand_total"] = self._fmt_id(getattr(instance, "grand_total", 0) or 0)
            if "down_payment_percent" in self.fields:
                raw = getattr(instance, "down_payment_percent", 0) or 0
                self.initial["down_payment_percent"] = self._fmt_id(raw)


        # ===== ORIGIN/DESTINATION (SATU KALI SAJA) =====
        if "origin" in self.fields:
            self.fields["origin"].queryset = Location.objects.none()
            if self.is_bound:
                oid = (self.data.get(self.add_prefix("origin")) or "").strip()
                if oid:
                    self.fields["origin"].queryset = Location.objects.filter(pk=oid)
            elif is_edit and getattr(instance, "origin_id", None):
                self.fields["origin"].queryset = Location.objects.filter(pk=instance.origin_id)
                self.initial["origin"] = instance.origin_id  # supaya selected

        if "destination" in self.fields:
            self.fields["destination"].queryset = Location.objects.none()
            if self.is_bound:
                did = (self.data.get(self.add_prefix("destination")) or "").strip()
                if did:
                    self.fields["destination"].queryset = Location.objects.filter(pk=did)
            elif is_edit and getattr(instance, "destination_id", None):
                self.fields["destination"].queryset = Location.objects.filter(pk=instance.destination_id)
                self.initial["destination"] = instance.destination_id

       
        # styling massal
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
                if name in ("total_amount", "tax_amount", "grand_total", "kurs_idr", "qty", "price"):
                    if "text-end" not in css:
                        css += " text-end"
                w.attrs["class"] = css

        # create default angka
        if is_create and not self.is_bound:
            self.initial.setdefault("qty", "0,00")
            self.initial.setdefault("price", "0,00")
            self.initial.setdefault("total_amount", "0,00")
            self.initial.setdefault("tax_amount", "0,00")
            self.initial.setdefault("grand_total", "0,00")
            self.initial.setdefault("kurs_idr", "1,00")

        # total_amount read-only
        if "total_amount" in self.fields:
            self.fields["total_amount"].widget.attrs["readonly"] = True
            self.fields["total_amount"].help_text = "Otomatis: qty × price"

        if "discount_type" in self.fields:
            self.fields["discount_type"].required = False    

    def clean_down_payment_percent(self):
        value = self.cleaned_data.get("down_payment_percent")

        if value is None:
            return value

        if value < 0:
            raise forms.ValidationError("Tidak boleh negatif.")

        if value > 100:
            raise forms.ValidationError("Tidak boleh lebih dari 100%.")

        return value

    def clean(self):
        cleaned = super().clean()

        # ----- QTY / PRICE / TOTAL (DPP awal) -----
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
        cleaned["total_amount"] = total

        print("CLEAN DISCOUNT TYPE:", cleaned.get("discount_type"))
        print("POST RAW DISCOUNT:", self.data.get("discount_value"))
        print("CLEANED DISCOUNT:", cleaned.get("discount_value"))

        # Helper parse uang (bisa string "1.000,50" atau Decimal)
        def _money(name, default="0"):
            v = cleaned.get(name)
            if v in (None, ""):
                return Decimal(default)
            return self._parse_id_decimal(v, name) if isinstance(v, str) else Decimal(str(v))

        # ----- DISCOUNT (mengurangi DPP) -----
        discount_type = cleaned.get("discount_type")  # "PERCENT" / "AMOUNT" / None
        discount_value = _money("discount_value", "0").quantize(Decimal("0.01"))

        if discount_value < 0:
            self.add_error("discount_value", "Discount tidak boleh negatif.")

        discount_amount = Decimal("0.00")
        if discount_type and discount_value and not self.errors.get("discount_value"):
            base = total

            if discount_type == "AMOUNT":
                discount_amount = min(discount_value, base)

            elif discount_type == "PERCENT":
                # persent max 100
                pct = min(discount_value, Decimal("100"))
                discount_amount = (base * pct / Decimal("100")).quantize(Decimal("0.01"))

        taxable_base = max(total - discount_amount, Decimal("0.00"))

        # ----- TAX/PPH/GRAND (SERVER-SIDE SOURCE OF TRUTH) -----
        ppn_rate_sum = Decimal("0.00")
        taxes = cleaned.get("taxes")  # ModelMultipleChoiceField -> iterable Tax
 
        if taxes:
            for t in taxes:
                rate = Decimal(str(getattr(t, "rate", 0) or 0))
                is_withholding = getattr(t, "is_withholding", None)

                if is_withholding is None:
                    is_withholding = (getattr(t, "group", "") == "PPH")

                # ✅ Abaikan PPh di JO
                if not is_withholding:
                    ppn_rate_sum += rate

        # ✅ Hitung hanya PPN
        tax_amount = (taxable_base * ppn_rate_sum / Decimal("100")).quantize(Decimal("0.01"))

        # ✅ Grand total TANPA pengurangan PPh
        grand_total = (taxable_base + tax_amount).quantize(Decimal("0.01"))

        cleaned["tax_amount"] = tax_amount
        cleaned["grand_total"] = grand_total
        cleaned["discount_value"] = discount_value


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
