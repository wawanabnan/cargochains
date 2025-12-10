# sales/forms_job_cost.py

from decimal import Decimal, InvalidOperation

from django import forms
from django.forms import inlineformset_factory

from .job_order_model import JobOrder, JobCost


class JobCostForm(forms.ModelForm):
    """
    Satu baris Job Cost:
    - qty, price, amount pakai string format Indonesia (1.000,00)
    - description, qty, price WAJIB kalau salah satunya diisi
    """

    # pakai CharField supaya bebas format
    qty = forms.CharField(required=False)
    price = forms.CharField(required=False)
    amount = forms.CharField(required=False)

    class Meta:
        model = JobCost
        fields = ["description", "qty", "price", "amount"]
        widgets = {
            "description": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            # qty/price/amount override di __init__, jadi di sini bebas
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # styling untuk qty/price/amount
        for name in ("qty", "price", "amount"):
            w = self.fields[name].widget
            css = "form-control form-control-sm text-end border-0 border-bottom rounded-0"
            w.attrs.setdefault("class", css)

        # amount readonly
        self.fields["amount"].widget.attrs["readonly"] = "readonly"

        # default tampilan 0,00 untuk form baru
        if not self.instance.pk and not self.is_bound:
            self.initial.setdefault("qty", "0,00")
            self.initial.setdefault("price", "0,00")
            self.initial.setdefault("amount", "0,00")

        # form edit: Decimal → string Indonesia
        if self.instance.pk and not self.is_bound:
            if self.instance.qty is not None:
                self.initial["qty"] = self._format_id(self.instance.qty)
            if self.instance.price is not None:
                self.initial["price"] = self._format_id(self.instance.price)
            if self.instance.amount is not None:
                self.initial["amount"] = self._format_id(self.instance.amount)

    # ---------- helper format / parse Indonesia ----------

    def _format_id(self, value: Decimal) -> str:
        """
        Decimal(1234.5) -> '1.234,50'
        """
        s = f"{value:.2f}"          # '1234.50'
        whole, frac = s.split(".")  # '1234', '50'

        # tambah titik ribuan manual
        rev = whole[::-1]
        parts = [rev[i:i+3] for i in range(0, len(rev), 3)]
        whole_id = ".".join(p[::-1] for p in parts[::-1])  # 1234 -> 1.234

        return f"{whole_id},{frac}"

    def _parse_id(self, s: str, label: str) -> Decimal:
        """
        '1.234,50' -> Decimal('1234.50')
        """
        if s in (None, ""):
            return Decimal("0")
        s = str(s).strip()
        s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            raise forms.ValidationError(
                f"Format {label} tidak valid. Gunakan contoh: 1.000,00"
            )

    # ---------- clean field ----------

    def clean_qty(self):
        val = self.cleaned_data.get("qty")
        return self._parse_id(val, "Qty")

    def clean_price(self):
        val = self.cleaned_data.get("price")
        return self._parse_id(val, "Price")

    def clean_amount(self):
        # amount sebenarnya dihitung di model.save(), tapi kita parse saja
        val = self.cleaned_data.get("amount")
        return self._parse_id(val, "Amount")

    def clean(self):
        cleaned = super().clean()

        desc = cleaned.get("description")
        qty = cleaned.get("qty")     # ini sudah Decimal dari clean_qty
        price = cleaned.get("price") # Decimal dari clean_price

        # Kalau semua kosong → row dianggap kosong, valid
        if not desc and qty == Decimal("0") and price == Decimal("0"):
            return cleaned

        errors = {}
        if not desc:
            errors["description"] = "Description wajib diisi."
        if qty in (None, Decimal("0")):
            errors["qty"] = "Qty wajib diisi."
        if price in (None, Decimal("0")):
            errors["price"] = "Price wajib diisi."

        if errors:
            raise forms.ValidationError(errors)

        return cleaned


# ---------- inline formset ----------

JobCostFormSet = inlineformset_factory(
    JobOrder,
    JobCost,
    form=JobCostForm,
    fields=["description", "qty", "price", "amount"],
    extra=0,
    can_delete=True,
)
