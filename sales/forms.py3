from datetime import timedelta,date
from django import forms
from django.forms import BaseInlineFormSet, HiddenInput, Select, inlineformset_factory
from django.utils import timezone

from . import models as m
from .models import SalesQuotation, SalesQuotationLine
from partners.models import Partner

from decimal import Decimal


from .freight import FreightQuotation
from geo.models import Location
from core.models import Currency, CoreSetting



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


# FormSet yang dipakai view
#QuotationLineFormSet = inlineformset_factory(
#   parent_model=SalesQuotation,
#    model=SalesQuotationLine,
#    form=QuotationLineForm,
#    formset=BaseLineFormSet,
#    extra=0,
#    can_delete=False,
#    validate_min=True,
#    min_num=1,
#)



class FreightQuotationForm(forms.ModelForm):
    """
    Form header Freight Quotation:
    - customer, origin, destination, service
    - currency, amount, tax_percent
    - cargo info (optional)
    - quotation_date, valid_until, tax_amount, total_amount di-set otomatis
    """

    class Meta:
        model = FreightQuotation
        fields = [
            "customer",
            "origin",
            "destination",
            "sales_service",
            "currency",
            "amount",
            "tax_percent",
            "valid_until",
            "payment_term",

            # CARGO
            "cargo_name",
            "hs_code",
            "commodity",
            "package_count",
            "package_type",
            "gross_weight",
            "weight_uom",
            "volume_cbm",
            "volume_uom",
            "is_dg",
            "dg_class",

            "ready_date",
            "notes_customer",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select", "id": "id_customer"}),
            "valid_until": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            # origin/destination dipakai via hidden + autocomplete,
            # queryset kita kosongkan dulu di __init__
            "origin": forms.Select(attrs={"class": "form-select d-none", "id": "id_origin"}),
            "destination": forms.Select(attrs={"class": "form-select d-none", "id": "id_destination"}),

            "sales_service": forms.Select(attrs={"class": "form-select"}),

            "currency": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "tax_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),

            # CARGO
            "cargo_name": forms.TextInput(attrs={"class": "form-control"}),
            "hs_code": forms.TextInput(attrs={"class": "form-control"}),
            "commodity": forms.TextInput(attrs={"class": "form-control"}),

            "package_count": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "package_type": forms.TextInput(attrs={"class": "form-control"}),

            "gross_weight": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "weight_uom": forms.TextInput(attrs={"class": "form-control"}),

            "volume_cbm": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "volume_uom": forms.TextInput(attrs={"class": "form-control"}),

            "is_dg": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "dg_class": forms.TextInput(attrs={"class": "form-control"}),

            "ready_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),

            "notes_customer": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        # simpan user untuk isi sales_user otomatis
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._user = user

        # --- Customer queryset: hanya perusahaan, urut company_name/name ---
        if "customer" in self.fields:
            self.fields["customer"].queryset = (
                Partner.objects.filter(is_individual=False)
                .order_by("company_name", "name")
            )

        # --- Currency diurutkan by code ---
        if "currency" in self.fields:
            self.fields["currency"].queryset = Currency.objects.all().order_by("code")

        # --- Field-field optional: jangan paksa required ---
        optional_fields = [
            "sales_service", "currency",
            "cargo_name", "hs_code", "commodity",
            "package_count", "package_type",
            "gross_weight", "weight_uom",
            "volume_cbm", "volume_uom",
            "is_dg", "dg_class",
            "ready_date", "notes_customer",
        ]
        for fname in optional_fields:
            if fname in self.fields:
                self.fields[fname].required = False

        # --- Origin / Destination: jangan load semua location ---
        if "origin" in self.fields:
            self.fields["origin"].queryset = Location.objects.none()
        if "destination" in self.fields:
            self.fields["destination"].queryset = Location.objects.none()

        if self.is_bound:
            # POST: isi queryset hanya id yang dipost → validasi tetap jalan, tapi ringan
            origin_id = self.data.get("origin")
            dest_id = self.data.get("destination")

            if origin_id and "origin" in self.fields:
                self.fields["origin"].queryset = Location.objects.filter(pk=origin_id)

            if dest_id and "destination" in self.fields:
                self.fields["destination"].queryset = Location.objects.filter(pk=dest_id)
        else:
            # EDIT: isi queryset dengan lokasi yang sedang dipakai saja
            if self.instance and self.instance.pk:
                if self.instance.origin_id and "origin" in self.fields:
                    self.fields["origin"].queryset = Location.objects.filter(
                        pk=self.instance.origin_id
                    )
                if self.instance.destination_id and "destination" in self.fields:
                    self.fields["destination"].queryset = Location.objects.filter(
                        pk=self.instance.destination_id
                    )

        for name in ["shipper", "consignee"]:
            if name in self.fields:
                self.fields[name].required = False

    def clean(self):
        cleaned = super().clean()

        sales_service = cleaned.get("sales_service")
        customer = cleaned.get("customer")

        # shipper basic info
        shipper = cleaned.get("shipper")
        shipper_province = cleaned.get("shipper_province")
        shipper_regency = cleaned.get("shipper_regency")
        shipper_district = cleaned.get("shipper_district")
        shipper_village = cleaned.get("shipper_village")
        shipper_address = cleaned.get("shipper_address")

        # consignee basic info
        consignee = cleaned.get("consignee")
        consignee_province = cleaned.get("consignee_province")
        consignee_regency = cleaned.get("consignee_regency")
        consignee_district = cleaned.get("consignee_district")
        consignee_village = cleaned.get("consignee_village")
        consignee_address = cleaned.get("consignee_address")

        # ======================
        # CUSTOMER ALWAYS REQUIRED
        # ======================
        if not customer:
            self.add_error("customer", "Customer wajib diisi.")

        # kalau service belum dipilih, error default handle sendiri
        if not sales_service:
            return cleaned

        code = (getattr(sales_service, "code", "") or "").upper()
        is_d2d = "D2D" in code       # Door to Door
        is_d2p = "D2P" in code       # Door to Port

        # ======================
        # DOOR TO DOOR RULES
        # ======================
        if is_d2d:
            # shipper wajib
            if not shipper:
                self.add_error("shipper", "Shipper wajib diisi untuk Door to Door.")

            # alamat shipper wajib lengkap
            if not shipper_province:
                self.add_error("shipper_province", "Provinsi shipper wajib diisi.")
            if not shipper_regency:
                self.add_error("shipper_regency", "Kabupaten/kota shipper wajib diisi.")
            if not shipper_district:
                self.add_error("shipper_district", "Kecamatan shipper wajib diisi.")
            if not shipper_village:
                self.add_error("shipper_village", "Kelurahan shipper wajib diisi.")
            if not shipper_address:
                self.add_error("shipper_address", "Alamat shipper wajib diisi.")

            # consignee wajib
            if not consignee:
                self.add_error("consignee", "Consignee wajib diisi untuk Door to Door.")

            # alamat consignee wajib lengkap
            if not consignee_province:
                self.add_error("consignee_province", "Provinsi consignee wajib diisi.")
            if not consignee_regency:
                self.add_error("consignee_regency", "Kabupaten/kota consignee wajib diisi.")
            if not consignee_district:
                self.add_error("consignee_district", "Kecamatan consignee wajib diisi.")
            if not consignee_village:
                self.add_error("consignee_village", "Kelurahan consignee wajib diisi.")
            if not consignee_address:
                self.add_error("consignee_address", "Alamat consignee wajib diisi.")

        # ======================
        # DOOR TO PORT RULES
        # ======================
        elif is_d2p:
            # hanya customer wajib
            pass

        # ======================
        # OTHER SERVICES
        # treat as Door to Port (minimum requirement)
        # ======================
        else:
            pass

        return cleaned

    def save(self, commit=True):
        """
        - Set sales_user dari user kalau belum ada
        - Auto quotation_date (kalau kosong)
        - Auto valid_until (CoreSetting.freight_quotation_valid_days atau default 7 hari)
        - Hitung tax_amount & total_amount dari amount & tax_percent
        """
        obj: FreightQuotation = super().save(commit=False)

        # sales person auto dari user
        if self._user and not obj.sales_user_id:
            obj.sales_user = self._user

        # quotation_date default hari ini kalau belum diisi
        if not obj.quotation_date:
            obj.quotation_date = date.today()

        # valid_until dari CoreSetting.freight_quotation_valid_days, fallback 7
        valid_days = 7
        try:
            settings = CoreSetting.objects.first()
            if settings and getattr(settings, "freight_quotation_valid_days", None):
                valid_days = settings.freight_quotation_valid_days
        except Exception:
            # kalau setting error, diam-diam pakai default 7
            pass

        if not obj.valid_until:
            obj.valid_until = obj.quotation_date + timedelta(days=valid_days)

        # hitung pajak
        amount = self.cleaned_data.get("amount") or Decimal("0")
        tax_percent = self.cleaned_data.get("tax_percent") or Decimal("0")

        obj.tax_amount = (amount * tax_percent) / Decimal("100")
        obj.total_amount = amount + obj.tax_amount

        if commit:
            obj.save()
            self.save_m2m()

        return obj