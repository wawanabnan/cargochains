from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory

from job.models.job_costs import JobCost, JobCostType
from job.models.job_orders import JobOrder
from core.models.currencies import Currency
from decimal import Decimal, ROUND_HALF_UP


# ==============================
# FORMAT & PARSE ANGKA (DIPERTAHANKAN)
# ==============================

def fmt_idr(val):
    if val is None:
        return ""
    try:
        val = Decimal(val)
    except Exception:
        return str(val)
    s = f"{val:,.2f}"              # 1,234,567.89
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234.567,89
    return s


def parse_money(s: str) -> Decimal:
    if s is None:
        return Decimal("0")
    s = str(s).strip()
    if s == "":
        return Decimal("0")

    # format Indonesia (1.234,56)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
        return Decimal(s)

    # format EN / DB (1234.56)
    return Decimal(s)


# ==============================
# FORM
# ==============================

class JobCostForm(forms.ModelForm):
    """
    Job Cost:
    - est_amount & actual_amount pakai format Indonesia
    - vendor optional
    - jika vendor kosong maka internal_note wajib
    """

    qty = forms.DecimalField(required=False, initial=1)
    price = forms.CharField(required=False, label="Unit Price")
    rate = forms.CharField(required=False, label="Rate")

    est_amount = forms.CharField(required=False, label="Est Amount")
    actual_amount = forms.CharField(required=False, label="Actual Amount")

    #qty = forms.CharField(required=False, label="Qty", initial="1,00")
    qty = forms.CharField(required=False)


    class Meta:
        
        model = JobCost
        fields = [
            "cost_type",
            "description",
            "qty",
            "price",
            "currency",
            "rate",
            "vendor",
            "internal_note",
            "est_amount",
            "actual_amount",

            
        ]
        widgets = {
            "cost_type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "description": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "placeholder": "Description"}
            ),
            "vendor": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "internal_note": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "placeholder": "Non-vendor text / internal note"}
            ),
            
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # =========================
        # REQUIRED / OPTIONAL (SAFE)
        # =========================
        for nm in ["cost_type", "description",  "est_amount"]:
            if nm in self.fields:
                self.fields[nm].required = True

        if "internal_note" in self.fields:
            self.fields["internal_note"].required = False


        # vendor/internal_note jangan dipaksa di level field
        if "vendor" in self.fields:
            self.fields["vendor"].required = False
        if "internal_note" in self.fields:
            self.fields["internal_note"].required = False

        if "est_amount" in self.fields:
            self.fields["est_amount"].required = False
            # buang atribut required kalau sempat kebawa
            self.fields["est_amount"].widget.attrs.pop("required", None)
            # readonly agar user tidak edit manual
            self.fields["est_amount"].widget.attrs["readonly"] = "readonly"

        # =========================
        # cost_type queryset + empty label
        # =========================
        if "cost_type" in self.fields:
            self.fields["cost_type"].queryset = (
                JobCostType.objects.filter(is_active=True)
                .order_by("sort_order", "name")
            )

            # hanya untuk row baru (instance belum ada)
            # NOTE: empty_label hanya berlaku untuk ModelChoiceField
            if hasattr(self.fields["cost_type"], "empty_label"):
                if not (self.instance and self.instance.pk):
                    self.fields["cost_type"].empty_label = "-- pilih cost type --"
                else:
                    self.fields["cost_type"].empty_label = None

            # widget attrs
            self.fields["cost_type"].widget.attrs.update({
                "class": "form-select form-select-sm",
            })

        # =========================
        # description
        # =========================
        if "description" in self.fields:
            self.fields["description"].widget.attrs.update({
                "class": "form-control form-control-sm",
                "placeholder": "Description",
                "autocomplete": "off",
            })

        # =========================
        # vendor (kalau ada)
        # =========================
        if "vendor" in self.fields:
            self.fields["vendor"].widget.attrs.update({
                "class": "form-select form-select-sm",
            })

        # =========================
        # internal_note (optional)
        # =========================
        if "internal_note" in self.fields:
            self.fields["internal_note"].widget.attrs.update({
                "class": "form-control form-control-sm",
                "placeholder": "Internal note (optional)",
                "autocomplete": "off",
            })

        
        # =========================
        # DEFAULT currency = IDR (row baru saja)
        # =========================
        if "currency" in self.fields:
            self.fields["currency"].queryset = Currency.objects.all().order_by("code")

            # hanya untuk row BARU (bukan edit existing)
            if not (self.instance and self.instance.pk):
                idr = Currency.objects.filter(code__iexact="IDR").first()
                if idr:
                    self.initial.setdefault("currency", idr.pk)

        
        # =========================
        # est_amount / actual_amount
        # =========================
        if "est_amount" in self.fields:
            self.fields["est_amount"].widget.attrs.update({
                "class": "form-control form-control-sm text-end js-money",
                "placeholder": "Est. Amount",
                "inputmode": "decimal",
                "autocomplete": "off",
            })

        if "actual_amount" in self.fields:
            self.fields["actual_amount"].widget.attrs.update({
                "class": "form-control form-control-sm text-end js-money",
                "placeholder": "Actual Amount",
                "inputmode": "decimal",
                "autocomplete": "off",
        })
            
        if "est_amount" in self.fields:
            self.fields["est_amount"].widget.attrs.update({
            "readonly": "readonly",
        })
        # =========================
        # qty / price / currency / rate
        # =========================
        if "qtyyyy" in self.fields:
            self.fields["qty"].widget.attrs.update({
                "class": "form-control form-control-sm text-end",
                "inputmode": "decimal",
                "autocomplete": "off",
            })


        if "qty" in self.fields:
            self.fields["qty"].widget = forms.TextInput(attrs={
                "class": "form-control form-control-sm text-end js-money",
                "inputmode": "decimal",
                "autocomplete": "off",
            })

            # edit mode: tampilkan 2 desimal Indo
            if self.instance and self.instance.pk and self.instance.qty is not None:
                self.initial["qty"] = fmt_idr(self.instance.qty)
            else:
                self.initial.setdefault("qty", "1,00")


        if "price" in self.fields:
            self.fields["price"].widget.attrs.update({
                "class": "form-control form-control-sm text-end js-money",
                "placeholder": "Unit Price",
                "inputmode": "decimal",
                "autocomplete": "off",
            })

        if "currency" in self.fields:
            self.fields["currency"].queryset = Currency.objects.all().order_by("code")
            self.fields["currency"].widget.attrs.update({
                "class": "form-select form-select-sm",
            })

        if "rate" in self.fields:
            self.fields["rate"].widget.attrs.update({
                "class": "form-control form-control-sm text-end js-money",
                "placeholder": "Rate",
                "inputmode": "decimal",
                "autocomplete": "off",
        })


        # initial formatted values (edit mode)
        if self.instance and self.instance.pk:
            if "qty" in self.fields:
                self.initial["qty"] = self.instance.qty
            if "price" in self.fields:
                self.initial["price"] = fmt_idr(getattr(self.instance, "price", None))
            if "rate" in self.fields:
                self.initial["rate"] = fmt_idr(getattr(self.instance, "rate", None))



        # =========================
        # initial formatted values (edit mode only)
        # =========================
        if self.instance and self.instance.pk:
            if "est_amount" in self.fields:
                self.initial["est_amount"] = fmt_idr(self.instance.est_amount)
            if "actual_amount" in self.fields:
                self.initial["actual_amount"] = fmt_idr(self.instance.actual_amount)

    
   #.........................................
    def clean_est_amount(self):
        return parse_money(self.cleaned_data.get("est_amount"))

    def clean_actual_amount(self):
        return parse_money(self.cleaned_data.get("actual_amount"))
    
    def clean_price(self):
        return parse_money(self.cleaned_data.get("price"))

    def clean_rate(self):
        v = parse_money(self.cleaned_data.get("rate"))
        return v if v > 0 else Decimal("1")



    def clean_backup(self):
        cleaned = super().clean()

        cost_type = cleaned.get("cost_type")
        
        desc = cleaned.get("description")
        vendor = cleaned.get("vendor")
        note = cleaned.get("internal_note")

        est = cleaned.get("est_amount") or Decimal("0")
        act = cleaned.get("actual_amount") or Decimal("0")

        # row kosong dianggap valid
        if not cost_type and not desc and not vendor and not note and est == Decimal("0") and act == Decimal("0"):
            return cleaned

        errors = {}

        if not cost_type:
            errors["cost_type"] = "Cost Type wajib dipilih."

        #if not vendor and not note:
        #    errors["internal_note"] = "Jika Vendor kosong, wajib isi keterangan (non-vendor)."

        requires_vendor = bool(getattr(cost_type, "requires_vendor", True))

        if requires_vendor and not vendor:
            self.add_error("vendor", "Vendor wajib diisi untuk cost type ini.")



        if est <= 0 and act <= 0:
            errors["est_amount"] = "Est Amount wajib diisi (minimal > 0)."

        if errors:
            raise forms.ValidationError(errors)

        return cleaned
       

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("DELETE"):
            return cleaned

        cost_type = cleaned.get("cost_type")
        vendor = cleaned.get("vendor")

        # cost_type wajib
        if not cost_type:
            self.add_error("cost_type", "Wajib pilih cost type.")
            return cleaned  # stop, karena rule lain tergantung cost_type

        # =========================
        # Parse Decimal aman
        # =========================
        qty = cleaned.get("qty") or 0
        qty = parse_money(qty)  or Decimal("0")
        
        if qty is None:
            qty = Decimal("0")

        if qty <= Decimal("0"):
            self.add_error("qty", "Qty harus > 0.")    

        price = cleaned.get("price")
        if not isinstance(price, Decimal):
            price = parse_money(price)

        rate = cleaned.get("rate")
        if not isinstance(rate, Decimal):
            rate = parse_money(rate)

        # =========================
        # VALIDASI INPUT DASAR
        # =========================
        if qty <= Decimal("0"):
            self.add_error("qty", "Qty harus > 0.")

        if price <= Decimal("0"):
            self.add_error("price", "Price harus > 0.")

        if rate is None or rate <= Decimal("0"):
            self.add_error("rate", "Rate harus > 0.")
            rate = Decimal("0")  # biar amount jadi 0 dan est_amount gagal juga

        # =========================
        # Vendor rule (INI YANG HILANG)
        # =========================
        requires_vendor = bool(getattr(cost_type, "requires_vendor", True))
        if requires_vendor and not vendor:
            self.add_error("vendor", "Vendor wajib diisi untuk cost type ini.")

        # =========================
        # AUTO CALC est_amount
        # =========================
        amount = qty * price * rate
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cleaned["est_amount"] = amount

        # est_amount wajib > 0
        if amount <= Decimal("0"):
            self.add_error("est_amount", "Estimasi wajib diisi (minimal > 0).")

        return cleaned
    

JobCostFormSet = inlineformset_factory(
    JobOrder,
    JobCost,
    form=JobCostForm,
    extra=0,
    can_delete=True,
)
