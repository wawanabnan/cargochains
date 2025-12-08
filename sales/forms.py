from datetime import timedelta,date
from django import forms
from django.forms import BaseInlineFormSet, HiddenInput, Select, inlineformset_factory
from django.utils import timezone

from . import models as m
from .models import SalesQuotation, SalesQuotationLine
from partners.models import Partner

from decimal import Decimal


from .freight import FreightQuotation,  FreightQuotationStatus, FreightOrder
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


#=============================================End Sales Quotation & Order================================
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.utils import timezone
from partners.models import Partner
from .freight import FreightQuotation, FreightQuotationStatus

class FreightQuotationForm(forms.ModelForm):

    class Meta:
        model = FreightQuotation
        exclude = ["sales_user"]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select", "id": "id_customer"}),
            "valid_until": forms.DateInput(
                attrs={
                    "class": "form-control",       # styling Bootstrap 5
                    "type": "date",                # native date picker
                    "data-role": "date-picker",    # buat selector JS
                    "placeholder": "yyyy-mm-dd",   # optional
                }
            ),
            "number": forms.HiddenInput(),
            "quotation_date": forms.HiddenInput(),
            "status": forms.HiddenInput(),
            # origin/destination dipakai via hidden + autocomplete,
            # queryset kita kosongkan dulu di __init__
            "origin": forms.Select(attrs={"class": "form-select d-none", "id": "id_origin"}),
            "destination": forms.Select(attrs={"class": "form-select d-none", "id": "id_destination"}),

            "sales_service": forms.Select(attrs={"class": "form-select"}),
            "sales_agency": forms.Select(attrs={"class": "form-select"}),
            "payment_term": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control text-end", "step": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control text-end", "step": "0.01"}),
            "amount": forms.NumberInput(attrs={"class": "form-control text-end", "step": "0.01"}),
            "tax_percent": forms.NumberInput(attrs={"class": "form-control text-end", "step": "0.01"}),
            "tax_amount": forms.NumberInput(attrs={"class": "form-control text-end", "step": "0.01", "readonly": "readonly"}),
            "total_amount": forms.NumberInput(attrs={"class": "form-control text-end", "step": "0.01", "readonly": "readonly"}),

            "number": forms.HiddenInput(),
            "quotation_date": forms.HiddenInput(),
            "status": forms.HiddenInput(),

            # CARGO
            "cargo_name": forms.TextInput(attrs={"class": "form-control"}),
            "hs_code": forms.TextInput(attrs={"class": "form-control"}),
            "commodity": forms.TextInput(attrs={"class": "form-control"}),

            "package_count": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "package_uom":  forms.Select(attrs={"class": "form-select"}),

            "gross_weight": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "weight_uom":  forms.Select(attrs={"class": "form-select"}),

            "volume_cbm": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "volume_uom": forms.Select(attrs={"class": "form-select"}),

            "is_dangerous_goods": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "dangerous_goods_class": forms.TextInput(attrs={"class": "form-control"}),

            "shipment_plan_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "data-role": "date-picker",
                }
            ),

            "notes_customer": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
             "quantity": forms.TextInput(
                attrs={"class": "form-control text-end fq-num-src"}
            ),
            "unit_price": forms.TextInput(
                attrs={"class": "form-control text-end fq-num-src"}
            ),
            "tax_percent": forms.TextInput(
                attrs={"class": "form-control text-end fq-num-src"}
            ),

            # TIGA INI DIHITUNG & DIFORMAT (baca saja)
            "amount": forms.TextInput(
                attrs={
                    "class": "form-control text-end fq-num-out",
                    "readonly": "readonly",
                }
            ),
            "tax_amount": forms.TextInput(
                attrs={
                    "class": "form-control text-end fq-num-out",
                    "readonly": "readonly",
                }
            ),
            "total_amount": forms.TextInput(
                attrs={
                    "class": "form-control text-end fq-num-out",
                    "readonly": "readonly",
                }
            ),
            "notes_customer": forms.Textarea(
                attrs={
                    "class": "form-control tinymce",  # class untuk inisialisasi TinyMCE
                    "rows": 4,
                    "placeholder": "Internal notes (price include / exclude, payment term, conditions, etc.)",
                }
            ),
            
            "discount_percent": forms.TextInput(
                attrs={"class": "form-control text-end fq-num-src"}
            ),
            "discount_amount": forms.TextInput(
                attrs={
                    "class": "form-control text-end fq-num-out",
                    "readonly": "readonly",
                }
            ),

        }

    
    def __init__(self, *args, **kwargs):
        # View kadang mengirim user=..., jangan dilempar ke super()
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # 1) Default: semua field tidak wajib dulu
        for f in self.fields.values():
            f.required = False

        # 2) Hanya 4 field header ini yang benar-benar wajib
        REQUIRED_FIELDS = [
            "customer",
            "sales_service",
            "payment_term",
            "currency",
            "origin_id",
            "destination_id",
             # CARGO INFO
            "cargo_name",
            "shipment_plan_date",
        ]
        for name in REQUIRED_FIELDS:
            if name in self.fields:
                self.fields[name].required = True

        # 3) Styling basic (optional, biar rapi)
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = (css + " form-select").strip()
            else:
                field.widget.attrs["class"] = (css + " form-control").strip()

        # --- DROPDOWN / QUERYSET PARTNER ---

        # Customer → filter role_type=customer kalau ada datanya
        if "customer" in self.fields:
            try:
                ids = PartnerRole.objects.filter(
                    role_type__code__iexact="customer"
                ).values_list("partner_id", flat=True)
                qs = Partner.objects.filter(id__in=ids).distinct()
            except Exception:
                qs = Partner.objects.all()
            self.fields["customer"].queryset = qs.order_by("name")
            self.fields["customer"].empty_label = "— pilih customer —"

        # shipper / consignee: queryset penuh dulu,
        # karena di UI kita pakai autocomplete + hidden field `name="shipper"/"consignee"`
        if "shipper" in self.fields:
            self.fields["shipper"].queryset = Partner.objects.all().order_by("name")
            self.fields["shipper"].empty_label = "— pilih shipper —"

        if "consignee" in self.fields:
            self.fields["consignee"].queryset = Partner.objects.all().order_by("name")
            self.fields["consignee"].empty_label = "— pilih consignee —"

        # sales_agency → filter role agency kalau ada
        if "sales_agency" in self.fields:
            try:
                ids = PartnerRole.objects.filter(
                    role_type__code__iexact="agency"
                ).values_list("partner_id", flat=True)
                qs = Partner.objects.filter(id__in=ids).distinct()
                self.fields["sales_agency"].queryset = qs.order_by("name")
            except Exception:
                self.fields["sales_agency"].queryset = Partner.objects.none()

            self.fields["sales_agency"].empty_label = "— pilih agency —"
  

from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.utils import timezone

from partners.models import Partner, PartnerRole
from geo.models import Location
from core.models import Currency, UOM, PaymentTerm
from .freight import FreightQuotation, FreightQuotationStatus

#-----------------------------------
class FreightQuotationForm(forms.ModelForm):
    class Meta:
        model = FreightQuotation
        # sales_user diisi otomatis dari request.user di view
        exclude = ["sales_user"]
        widgets = {
            # HEADER
            "number": forms.HiddenInput(),
            "quotation_date": forms.HiddenInput(),
            "status": forms.HiddenInput(),

            "customer": forms.Select(
                attrs={"class": "form-select", "id": "id_customer"}
            ),
            "sales_service": forms.Select(attrs={"class": "form-select"}),
            "sales_agency": forms.Select(attrs={"class": "form-select"}),
            "payment_term": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.Select(attrs={"class": "form-select"}),

            "valid_until": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "data-role": "date-picker",
                    "placeholder": "yyyy-mm-dd",
                }
            ),
            "shipment_plan_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "data-role": "date-picker",
                }
            ),

            # ORIGIN / DESTINATION (hidden, diisi via autocomplete)
            "origin": forms.Select(
                attrs={"class": "form-select d-none", "id": "id_origin"}
            ),
            "destination": forms.Select(
                attrs={"class": "form-select d-none", "id": "id_destination"}
            ),

            # CARGO
            "cargo_name": forms.TextInput(attrs={"class": "form-control"}),
            "hs_code": forms.TextInput(attrs={"class": "form-control"}),
            "commodity": forms.TextInput(attrs={"class": "form-control"}),

            "package_count": forms.NumberInput(
                attrs={"class": "form-control", "step": "1", "min": "0"}
            ),
            "package_uom": forms.Select(attrs={"class": "form-select"}),

            "gross_weight": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "weight_uom": forms.Select(attrs={"class": "form-select"}),

            "volume_cbm": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.001"}
            ),
            "volume_uom": forms.Select(attrs={"class": "form-select"}),

            "is_dangerous_goods": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "dangerous_goods_class": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            # PRICING
            "quantity": forms.TextInput(
                attrs={"class": "form-control text-end fq-num-src"}
            ),
            "unit_price": forms.TextInput(
                attrs={"class": "form-control text-end fq-num-src"}
            ),
            "discount_percent": forms.TextInput(
                attrs={"class": "form-control text-end fq-num-src"}
            ),
            "discount_amount": forms.TextInput(
                attrs={
                    "class": "form-control text-end",
                    "readonly": "readonly",
                }
            ),
            "tax_percent": forms.TextInput(
                attrs={"class": "form-control text-end fq-num-src"}
            ),
            "tax_amount": forms.TextInput(
                attrs={
                    "class": "form-control text-end",
                    "readonly": "readonly",
                }
            ),
            "amount": forms.TextInput(
                attrs={
                    "class": "form-control text-end",
                    "readonly": "readonly",
                }
            ),
            "total_amount": forms.TextInput(
                attrs={
                    "class": "form-control text-end",
                    "readonly": "readonly",
                }
            ),

            # NOTES
            "notes_customer": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "notes_internal": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }

    def __init__(self, *args, **kwargs):
        # View boleh kirim user=...
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Tinggi textarea address
        for name in ["shipper_address", "consignee_address"]:
            if name in self.fields:
                self.fields[name].widget.attrs["rows"] = 3

        # Pastikan semua TextInput/Textarea/NumberInput punya form-control,
        # dan semua Select punya form-select (jaga-jaga kalau ada yang lupa di Meta.widgets)
        for name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.TextInput, forms.Textarea, forms.NumberInput)):
                existing = widget.attrs.get("class", "")
                widget.attrs["class"] = (existing + " form-control").strip()

            if isinstance(widget, forms.Select):
                existing = widget.attrs.get("class", "")
                widget.attrs["class"] = (existing + " form-select").strip()

        today = timezone.now().date()

        # Hanya untuk CREATE (instance belum ada)
        if not (self.instance and self.instance.pk):
            # quotation_date hidden → set ke hari ini kalau belum ada
            if "quotation_date" in self.fields and not (
                self.initial.get("quotation_date") or self.fields["quotation_date"].initial
            ):
                self.initial["quotation_date"] = today

            # valid_until: quotation_date + 7 hari
            if "valid_until" in self.fields and not (
                self.initial.get("valid_until") or self.fields["valid_until"].initial
            ):
                self.initial["valid_until"] = today + timezone.timedelta(days=7)

        # 1) Default: semua optional dulu
        for f in self.fields.values():
            f.required = False

        # 2) Field yang wajib (header utama)
        REQUIRED_FIELDS = [
            "customer",
            "sales_service",
            "payment_term",
            "currency",
            "shipment_plan_date",
            "cargo_name",
        ]
        for name in REQUIRED_FIELDS:
            if name in self.fields:
                self.fields[name].required = True

        # 3) Filter CUSTOMER by role (kalau ada PartnerRole)
        if "customer" in self.fields:
            try:
                ids = PartnerRole.objects.filter(
                    role_type__code__iexact="customer"
                ).values_list("partner_id", flat=True)
                qs = Partner.objects.filter(id__in=ids).distinct()
            except Exception:
                qs = Partner.objects.all()
            self.fields["customer"].queryset = qs.order_by("name")
            self.fields["customer"].empty_label = "— pilih customer —"

        # 4) shipper / consignee: queryset penuh dulu (di UI pakai autocomplete)
        if "shipper" in self.fields:
            self.fields["shipper"].queryset = Partner.objects.all().order_by("name")
            self.fields["shipper"].empty_label = "— pilih shipper —"
        if "consignee" in self.fields:
            self.fields["consignee"].queryset = Partner.objects.all().order_by("name")
            self.fields["consignee"].empty_label = "— pilih consignee —"

        # 5) sales_agency → filter Agency jika ada
        if "sales_agency" in self.fields:
            try:
                ids = PartnerRole.objects.filter(
                    role_type__code__iexact="agency"
                ).values_list("partner_id", flat=True)
                qs = Partner.objects.filter(id__in=ids).distinct()
                self.fields["sales_agency"].queryset = qs.order_by("name")
            except Exception:
                self.fields["sales_agency"].queryset = Partner.objects.none()

        # 6) Currency & UOM & PaymentTerm
        if "currency" in self.fields:
            self.fields["currency"].queryset = Currency.objects.all().order_by("code")

        # pakai kategori dari model (weight/volume/count)
        if "weight_uom" in self.fields:
            self.fields["weight_uom"].queryset = UOM.objects.filter(
                category__iexact="weight"
            ).order_by("name")
        if "volume_uom" in self.fields:
            self.fields["volume_uom"].queryset = UOM.objects.filter(
                category__iexact="volume"
            ).order_by("name")
        if "package_uom" in self.fields:
            self.fields["package_uom"].queryset = UOM.objects.filter(
                category__iexact="count"
            ).order_by("name")

        if "payment_term" in self.fields:
            self.fields["payment_term"].queryset = PaymentTerm.objects.all().order_by(
                "name"
            )

        # ============================
        # 7) GEO: SHIPPER & CONSIGNEE
        # ============================
        # default: children kosong
        geo_child_fields = [
            "shipper_regency",
            "shipper_district",
            "shipper_village",
            "consignee_regency",
            "consignee_district",
            "consignee_village",
        ]
        for name in geo_child_fields:
            if name in self.fields:
                self.fields[name].queryset = Location.objects.none()

        # provinces: isi semua
        for name in ["shipper_province", "consignee_province"]:
            if name in self.fields:
                self.fields[name].queryset = Location.objects.filter(
                    kind="province"
                ).order_by("name")

        # Helper untuk bind anak geo berdasarkan POST / instance
        def _bind_geo(prefix: str):
            prov_field = f"{prefix}_province"
            reg_field = f"{prefix}_regency"
            dist_field = f"{prefix}_district"
            vill_field = f"{prefix}_village"

            prov_id = None
            reg_id = None
            dist_id = None

            if self.is_bound:
                # ADD & EDIT (POST) – ambil dari data yang dikirim user
                prov_id = self.data.get(prov_field) or None
                reg_id = self.data.get(reg_field) or None
                dist_id = self.data.get(dist_field) or None
            elif self.instance and self.instance.pk:
                # EDIT (GET) – ambil dari instance
                prov_id = getattr(self.instance, f"{prov_field}_id", None)
                reg_id = getattr(self.instance, f"{reg_field}_id", None)
                dist_id = getattr(self.instance, f"{dist_field}_id", None)

            if prov_id and reg_field in self.fields:
                self.fields[reg_field].queryset = Location.objects.filter(
                    parent_id=prov_id
                ).order_by("name")

            if reg_id and dist_field in self.fields:
                self.fields[dist_field].queryset = Location.objects.filter(
                    parent_id=reg_id
                ).order_by("name")

            if dist_id and vill_field in self.fields:
                self.fields[vill_field].queryset = Location.objects.filter(
                    parent_id=dist_id
                ).order_by("name")

        _bind_geo("shipper")
        _bind_geo("consignee")

    def clean(self):
        cleaned = super().clean()

        # === 1) TANGGAL & STATUS OTOMATIS ===
        today = timezone.now().date()

        if not cleaned.get("quotation_date"):
            cleaned["quotation_date"] = today

        if not cleaned.get("status"):
            cleaned["status"] = FreightQuotationStatus.DRAFT

        # === 2) VALID UNTIL: +7 hari jika kosong ===
        valid_until = cleaned.get("valid_until")
        if not valid_until:
            base_date = cleaned.get("quotation_date") or today
            cleaned["valid_until"] = base_date + timezone.timedelta(days=7)

        # === 3) HEADER WAJIB (tambahan proteksi untuk customer) ===
        if not cleaned.get("customer"):
            self.add_error("customer", "Customer wajib diisi.")

        # === 4) PRICING (qty, price, discount, tax → amount, total) ===
        TWO = Decimal("0.01")

        qty = cleaned.get("quantity") or Decimal("1")
        unit_price = cleaned.get("unit_price") or Decimal("0")
        disc_pct = cleaned.get("discount_percent") or Decimal("0")
        tax_pct = cleaned.get("tax_percent") or Decimal("0")

        qty = Decimal(qty).quantize(TWO, rounding=ROUND_HALF_UP)
        unit_price = Decimal(unit_price).quantize(TWO, rounding=ROUND_HALF_UP)
        disc_pct = Decimal(disc_pct).quantize(TWO, rounding=ROUND_HALF_UP)
        tax_pct = Decimal(tax_pct).quantize(TWO, rounding=ROUND_HALF_UP)

        gross = (qty * unit_price).quantize(TWO, rounding=ROUND_HALF_UP)
        discount_amount = (gross * disc_pct / Decimal("100")).quantize(
            TWO, rounding=ROUND_HALF_UP
        )
        tax_base = (gross - discount_amount).quantize(TWO, rounding=ROUND_HALF_UP)
        tax_amount = (tax_base * tax_pct / Decimal("100")).quantize(
            TWO, rounding=ROUND_HALF_UP
        )
        total = (gross - discount_amount + tax_amount).quantize(
            TWO, rounding=ROUND_HALF_UP
        )

        cleaned["quantity"] = qty
        cleaned["unit_price"] = unit_price
        cleaned["discount_percent"] = disc_pct
        cleaned["discount_amount"] = discount_amount
        cleaned["tax_percent"] = tax_pct
        cleaned["amount"] = gross
        cleaned["tax_amount"] = tax_amount
        cleaned["total_amount"] = total

        # === 5) BUSINESS RULE: Shipper / Consignee berdasarkan sales_service ===
        service = cleaned.get("sales_service")
        code = (getattr(service, "code", "") or "").upper()

        is_d2d = code.startswith("D2D") or "DOOR TO DOOR" in code
        is_d2p = code.startswith("D2P") or "DOOR TO PORT" in code
        is_p2p = code.startswith("P2P") or "PORT TO PORT" in code

        def add_required(field_name, message):
            """
            Tambah error kalau field kosong.
            Field name mengikuti nama field di model:
            - shipper_contact_name, shipper_phone, shipper_address, shipper_province, ...
            - consignee_name, consignee_phone, consignee_address, consignee_province, ...
            """
            if field_name in self.errors:
                return
            if not cleaned.get(field_name):
                self.add_error(field_name, message)

        # =======================
        # D2D
        # =======================
        # D2D: shipper & consignee WAJIB
        # nama, telp, alamat, GEO (province–village)
        if is_d2d:
            # SHIPPER
            add_required("shipper_contact_name", "Nama shipper wajib diisi untuk layanan Door to Door.")
            add_required("shipper_phone", "Telepon shipper wajib diisi untuk layanan Door to Door.")
            add_required("shipper_address", "Alamat shipper wajib diisi untuk layanan Door to Door.")
            add_required("shipper_province", "Provinsi shipper wajib diisi untuk layanan Door to Door.")
            add_required("shipper_regency", "Kabupaten/Kota shipper wajib diisi untuk layanan Door to Door.")
            add_required("shipper_district", "Kecamatan shipper wajib diisi untuk layanan Door to Door.")
            add_required("shipper_village", "Kelurahan/Desa shipper wajib diisi untuk layanan Door to Door.")

            # CONSIGNEE
            add_required("consignee_name", "Nama consignee wajib diisi untuk layanan Door to Door.")
            add_required("consignee_phone", "Telepon consignee wajib diisi untuk layanan Door to Door.")
            add_required("consignee_address", "Alamat consignee wajib diisi untuk layanan Door to Door.")
            add_required("consignee_province", "Provinsi consignee wajib diisi untuk layanan Door to Door.")
            add_required("consignee_regency", "Kabupaten/Kota consignee wajib diisi untuk layanan Door to Door.")
            add_required("consignee_district", "Kecamatan consignee wajib diisi untuk layanan Door to Door.")
            add_required("consignee_village", "Kelurahan/Desa consignee wajib diisi untuk layanan Door to Door.")

        # =======================
        # D2P
        # =======================
        # D2P:
        # - Shipper WAJIB full: nama, telp, alamat, GEO
        # - Consignee WAJIB: nama, telp, alamat (GEO boleh kosong)
        elif is_d2p:
            # SHIPPER
            add_required("shipper_contact_name", "Nama shipper wajib diisi untuk layanan Door to Port.")
            add_required("shipper_phone", "Telepon shipper wajib diisi untuk layanan Door to Port.")
            add_required("shipper_address", "Alamat shipper wajib diisi untuk layanan Door to Port.")
            add_required("shipper_province", "Provinsi shipper wajib diisi untuk layanan Door to Port.")
            add_required("shipper_regency", "Kabupaten/Kota shipper wajib diisi untuk layanan Door to Port.")
            add_required("shipper_district", "Kecamatan shipper wajib diisi untuk layanan Door to Port.")
            add_required("shipper_village", "Kelurahan/Desa shipper wajib diisi untuk layanan Door to Port.")

            # CONSIGNEE (tanpa GEO)
            add_required("consignee_name", "Nama consignee wajib diisi untuk layanan Door to Port.")
            add_required("consignee_phone", "Telepon consignee wajib diisi untuk layanan Door to Port.")
            add_required("consignee_address", "Alamat consignee wajib diisi untuk layanan Door to Port.")

        # =======================
        # P2P
        # =======================
        # P2P:
        # - Shipper & Consignee WAJIB nama, telp, alamat
        # - Semua GEO boleh kosong
        elif is_p2p:
            # SHIPPER
            add_required("shipper_contact_name", "Nama shipper wajib diisi untuk layanan Port to Port.")
            add_required("shipper_phone", "Telepon shipper wajib diisi untuk layanan Port to Port.")
            add_required("shipper_address", "Alamat shipper wajib diisi untuk layanan Port to Port.")

            # CONSIGNEE
            add_required("consignee_name", "Nama consignee wajib diisi untuk layanan Port to Port.")
            add_required("consignee_phone", "Telepon consignee wajib diisi untuk layanan Port to Port.")
            add_required("consignee_address", "Alamat consignee wajib diisi untuk layanan Port to Port.")

       
        # === 6) ORIGIN / DESTINATION FINAL LOGIC ===
        # D2D: origin & destination otomatis diambil dari shipper/consignee_village
        if is_d2d:
            shipper_village = cleaned.get("shipper_village")
            consignee_village = cleaned.get("consignee_village")

            # Kalau village ada dan origin/destination belum terisi, isi dari village
            if shipper_village and not cleaned.get("origin"):
                cleaned["origin"] = shipper_village

            if consignee_village and not cleaned.get("destination"):
                cleaned["destination"] = consignee_village

        # Semua layanan (D2D / D2P / P2P / lainnya):
        # origin & destination WAJIB terisi sebelum save
        if "origin" not in self.errors and not cleaned.get("origin"):
            self.add_error("origin", "Origin wajib diisi.")

        if "destination" not in self.errors and not cleaned.get("destination"):
            self.add_error("destination", "Destination wajib diisi.")

       
        return cleaned


#---------------------------------
# sales/forms.py
from django import forms
from decimal import Decimal, InvalidOperation

class GenerateOrderForm(forms.Form):
    REFERENCE_TYPES = [
        ("CUSTOMER_PO", "Customer PO"),
        ("EMAIL", "Email"),
        ("QUOTATION", "Quotation"),
    ]

    ref_type = forms.ChoiceField(
        label="Reference Type",
        choices=REFERENCE_TYPES,
        required=True,
    )

    ref_number = forms.CharField(
        label="Reference Number",
        required=True,
        max_length=100,
    )

    ref_date = forms.DateField(
        label="Sales Order Date",
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    down_payment = forms.CharField(
        label="Down Payment",
        required=False,
    )

    
    def clean_down_payment(self):
        raw = (self.cleaned_data.get("down_payment") or "").strip()

        # kosong -> anggap 0
        if not raw:
            return Decimal("0.00")

        # hapus spasi
        raw = raw.replace(" ", "")

        # "1.500.000,25" -> "1500000,25" -> "1500000.25"
        raw = raw.replace(".", "").replace(",", ".")

        try:
            value = Decimal(raw)
        except InvalidOperation:
            raise forms.ValidationError(
                "Format Down Payment tidak valid. Gunakan contoh: 1.500.000,00"
            )

        if value < 0:
            raise forms.ValidationError("Down Payment tidak boleh negatif.")

        return value

# sales/forms.py
from django import forms
from .freight import FreightOrder


class FreightOrderEditForm(forms.ModelForm):
    class Meta:
        model = FreightOrder
        fields = [
            "order_date",
            "reference_type",
            "reference_number",
            "down_payment",
        ]
        widgets = {
            "order_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                    "required": "required",
                }
            ),
            "reference_type": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": "required",
                }
            ),
            "reference_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": "50",
                    "required": "required",
                }
            ),
            # field asli untuk DB: hidden
            "down_payment": forms.HiddenInput(
                attrs={
                    "id": "id_down_payment",  # penting untuk JS
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["order_date"].required = True
        self.fields["reference_type"].required = True
        self.fields["reference_number"].required = True
        self.fields["down_payment"].required = False







#-------------------------------INVOICE AREA----------------------------------------------------#
# sales/forms.py

from django import forms
from .invoice import Invoice
from .freight import FreightOrder


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "freight_order",
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

        qs = FreightOrder.objects.select_related("customer").order_by("-id")
        self.fields["freight_order"].queryset = qs
        self.fields["freight_order"].widget.attrs.update({"class": "form-select"})

        # Styling
        for name, field in self.fields.items():
            if name != "freight_order":
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (css + " form-control").strip()

        # Kalau EDIT (instance sudah ada), lock freight_order
        if self.instance and self.instance.pk:
            self.fields["freight_order"].disabled = True        


class InvoiceGenerateForm(forms.Form):
    MODE_FULL = "FULL"
    MODE_CUSTOM = "CUSTOM"
    MODE_CHOICES = [
        (MODE_FULL, "Full amount (total Freight Order)"),
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
        help_text="Untuk mode FULL akan otomatis memakai total Freight Order.",
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



