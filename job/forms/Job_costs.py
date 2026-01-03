from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory

from job.models.costs import JobCost, JobCostType
from job.models.job_orders import JobOrder


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

    est_amount = forms.CharField(required=False, label="Est Amount")
    actual_amount = forms.CharField(required=False, label="Actual Amount")

    class Meta:
        model = JobCost
        fields = [
            "cost_type",
            "description",
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
        for nm in ["cost_type", "description", "vendor", "est_amount"]:
            if nm in self.fields:
                self.fields[nm].required = True

        if "internal_note" in self.fields:
            self.fields["internal_note"].required = False

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

        if not vendor and not note:
            errors["internal_note"] = "Jika Vendor kosong, wajib isi keterangan (non-vendor)."

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
        est = cleaned.get("est_amount")
        act = cleaned.get("actual_amount")

        # cost_type wajib
        if not cost_type:
            self.add_error("cost_type", "Wajib pilih cost type.")

      
        # est_amount wajib dan > 0
        # (kalau est bisa None karena field Char->Decimal, aman)
        est_val = est if isinstance(est, Decimal) else (Decimal("0") if not est else Decimal(str(est)))
        if est is None or est_val <= Decimal("0"):
            self.add_error("est_amount", "Estimasi wajib diisi (minimal > 0).")

        # internal_note optional -> tidak divalidasi

        return cleaned

JobCostFormSet = inlineformset_factory(
    JobOrder,
    JobCost,
    form=JobCostForm,
    extra=0,
    can_delete=True,
)
