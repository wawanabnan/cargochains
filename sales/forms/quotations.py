from datetime import timedelta,date
from django import forms
from django.forms import BaseInlineFormSet, HiddenInput, Select, inlineformset_factory
from django.utils import timezone

from  sales  import models as m
from ..models import SalesQuotation, SalesQuotationLine
from partners.models import Partner

from decimal import Decimal


from ..freight import FreightQuotation,  FreightQuotationStatus, FreightOrder
from geo.models import Location
from core.models import Currency, CoreSetting
from core.models import UOM



# sales/forms.py
from django.forms import inlineformset_factory

# opsional: kalau ada tabel junction PartnerRole
try:
    from partners.models import PartnerRole
except Exception:
    PartnerRole = None

# opsional: ambil setting hari berlaku
try:
    from core.utils import get_int_setting
except Exception:
    get_int_setting = None


# ==== Helper: sales service label ====
class SalesServiceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return getattr(obj, "name", str(obj))


# ================= HEADER FORM =================
class QuotationHeaderForm(forms.ModelForm):
    # terima dd-mm-YYYY + fallback ISO
    valid_until = forms.DateField(
        input_formats=["%d-%m-%Y", "%Y-%m-%d"],
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "dd-mm-YYYY",
            "autocomplete": "off",
            "data-date-format": "d-m-Y",
        }),
        required=False,
    )

    class Meta:
        model = m.SalesQuotation
        fields = [
            "customer",
            "sales_service",
            "sales_agency",
            "currency",
            "payment_term",
            "valid_until",
            "note_1",
            "date",        # hidden; server-side juga set
            "sales_user",  # hidden; server-side juga set
        ]
        widgets = {
            "customer":      forms.Select(attrs={"class": "form-select"}),
            "sales_service": forms.Select(attrs={"class": "form-select"}),
            "sales_agency":  forms.Select(attrs={"class": "form-select"}),
            "currency":      forms.Select(attrs={"class": "form-select"}),
            "payment_term":  forms.Select(attrs={"class": "form-select"}),
            "note_1":        forms.Textarea(attrs={"rows": 6, "class": "form-control"}),
            "date":          forms.HiddenInput(),
            "sales_user":    forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # hidden default
        if not self.is_bound and "date" in self.fields:
            self.initial["date"] = timezone.localdate().isoformat()
        if self.user and "sales_user" in self.fields:
            self.initial["sales_user"] = getattr(self.user, "pk", None)

        # auto valid_until = today + N (default 7 / dari core setting)
        days = 7
        try:
            days = int(get_int_setting("quotation_valid_days", 7)) if get_int_setting else 7
        except Exception:
            pass
        if not self.is_bound and "valid_until" in self.fields:
            self.initial["valid_until"] = (timezone.localdate() + timedelta(days=days)).strftime("%d-%m-%Y")

        # filter CUSTOMER: role_type.code = 'customer'
        if "customer" in self.fields:
            try:
                if PartnerRole is not None:
                    ids = PartnerRole.objects.filter(
                        role_type__code__iexact="customer"
                    ).values_list("partner_id", flat=True)
                    qs = Partner.objects.filter(id__in=ids).distinct()
                else:
                    qs = Partner.objects.filter(
                        roles__role_type__code__iexact="customer"
                    ).distinct()
                self.fields["customer"].queryset = qs.order_by("name")
            except Exception:
                pass
            self.fields["customer"].empty_label = "— pilih customer —"

        # filter AGENCY: role_type.code = 'agency'
        if "sales_agency" in self.fields:
            try:
                if PartnerRole is not None:
                    ids = PartnerRole.objects.filter(
                        role_type__code__iexact="agency"
                    ).values_list("partner_id", flat=True)
                    qs = Partner.objects.filter(id__in=ids).distinct()
                else:
                    qs = Partner.objects.filter(
                        roles__role_type__code__iexact="agency"
                    ).distinct()
                self.fields["sales_agency"].queryset = qs.order_by("name")
            except Exception:
                pass
            self.fields["sales_agency"].empty_label = "— pilih agency —"

        # label sales_service tanpa code
        if "sales_service" in self.fields:
            base = self.fields["sales_service"]
            self.fields["sales_service"] = SalesServiceChoiceField(
                queryset=getattr(base, "queryset", None),
                required=base.required,
                empty_label=getattr(base, "empty_label", "---------"),
                label=base.label or "Sales service",
                help_text=base.help_text,
                widget=base.widget,
            )

        # kunci sales_user untuk non supervisor (opsional)
        try:
            from .auth import is_sales_supervisor
            if self.user and not is_sales_supervisor(self.user):
                self.fields["sales_user"].disabled = True
        except Exception:
            pass


# ================= LINE FORM =================
class QuotationLineForm(forms.ModelForm):
    amount = forms.DecimalField(
    required=False,
    label="Amount",
    decimal_places=2,
    max_digits=18,
    widget=forms.TextInput(attrs={"readonly": "readonly", "class": "form-control money"})
    )

   
    class Meta:
        model = SalesQuotationLine
        fields = ["origin", "destination", "description", "uom", "qty", "price", "amount"]
        widgets = {
           
           "origin": forms.Select(attrs={"class": "form-select select2-location"}),
           "destination": forms.Select(attrs={"class": "form-select select2-location"}),

            "uom": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "qty": forms.TextInput(attrs={"class": "form-control money", "inputmode": "decimal"}),
            "price": forms.TextInput(attrs={"class": "form-control money", "inputmode": "decimal"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # tambah class bootstrap bila belum ada
        for f in self.fields.values():
            if isinstance(f.widget, HiddenInput):
                continue
            cls = f.widget.attrs.get("class", "")
            base = "form-select" if isinstance(f.widget, Select) else "form-control"
            if base not in cls:
                f.widget.attrs["class"] = (cls + " " + base).strip()

    # mandatory rules (baris harus lengkap)
    def clean(self):
        cleaned = super().clean()
        errs = {}
        if not cleaned.get("origin"):
            errs["origin"] = "Origin wajib diisi."
        if not cleaned.get("destination"):
            errs["destination"] = "Destination wajib diisi."
        if not cleaned.get("description"):
            errs["description"] = "Description wajib diisi."
        if not cleaned.get("uom"):
            errs["uom"] = "UoM wajib dipilih."
        if cleaned.get("qty") is None or cleaned.get("qty") <= 0:
            errs["qty"] = "Qty harus > 0."
        if cleaned.get("price") is None or cleaned.get("price") < 0:
            errs["price"] = "Price tidak boleh negatif."
        if errs:
            for k, v in errs.items():
                self.add_error(k, v)
        return cleaned


# ================= FORMSET =================
class BaseLineFormSet(BaseInlineFormSet):
    """Validasi gabungan untuk seluruh baris."""
    def clean(self):
        super().clean()

        # kalau sudah ada error per-form (field errors), jangan tambah non_form_error berulang
        if any(f.errors for f in self.forms):
            return

        any_filled = False
        line_errors = []

        for idx, f in enumerate(self.forms, start=1):
            cd = getattr(f, "cleaned_data", None) or {}
            if cd.get("DELETE"):
                continue

            filled = any(cd.get(k) for k in ("origin", "destination", "description", "uom", "qty", "price"))
            if not filled:
                continue  # baris kosong: abaikan (tidak dianggap valid)

            any_filled = True

            missing = []
            for k in ("origin", "destination", "description", "uom"):
                if not cd.get(k):
                    missing.append(k)
            if cd.get("qty") is None or cd.get("qty") <= 0:
                missing.append("qty")
            if cd.get("price") is None or cd.get("price") < 0:
                missing.append("price")

            if missing:
                # tandai ke field masing-masing (sekali per field)
                for k in set(missing):
                    f.add_error(k, "Wajib diisi dengan benar.")
                # tampung pesan baris untuk ditampilkan sekali di atas
                line_errors.append(f"Baris belum lengkap: {idx}. Lengkapi atau kosongkan sepenuhnya.")

        # kalau ada baris terisi tapi belum lengkap → tampilkan pesan gabungan SEKALI
        if line_errors:
            raise forms.ValidationError(line_errors)

        # tidak ada satu pun baris valid terisi → beri satu pesan saja
        if not any_filled:
            raise forms.ValidationError("Minimal satu line valid harus diisi.")





