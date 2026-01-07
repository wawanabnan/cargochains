# sales/forms/vendors.py
from decimal import Decimal, InvalidOperation
from django import forms
from geo.models import Location
from partners.models import Partner, PartnerRole, PartnerRoleTypes


def get_vendor_role_type():
    return PartnerRoleTypes.objects.get(code__iexact="vendor")


class VendorForm(forms.ModelForm):
    # GEO pakai IntegerField (stabil, anti "not a valid choice")
    province = forms.IntegerField(
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_province"}),
        label="Provinsi",
    )
    regency = forms.IntegerField(
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_regency"}),
        label="Kab/Kota",
    )
    district = forms.IntegerField(
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_district"}),
        label="Kecamatan",
    )
    village = forms.IntegerField(
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_village"}),
        label="Kelurahan / Desa",
    )

    class Meta:
        model = Partner
        exclude = ["province", "regency", "district", "village", "location", "roles"]

        # ✅ sama persis dengan customer (biar template+JS bisa reuse)
        fields = [
            "is_individual",

            "name",
            "company_name",
            "company_type",
            "is_pkp",
            "tax",

            "sales_user",

            "province", "regency", "district", "village",
            "post_code", "address_line1", "address_line2",
            "city", "country",

            "bank_name", "bank_account", "bank_account_name"
        ]

        widgets = {
            "is_individual": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_pkp": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "name": forms.TextInput(attrs={"class": "form-control"}),
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_type": forms.Select(attrs={"class": "form-select"}),
            "tax": forms.TextInput(attrs={"class": "form-control"}),

            "sales_user": forms.Select(attrs={"class": "form-select"}),

            "post_code": forms.TextInput(attrs={"class": "form-control"}),
            "address_line1": forms.TextInput(attrs={"class": "form-control"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),

            "bank_name": forms.TextInput(attrs={"class": "form-control"}),
            "bank_account": forms.TextInput(attrs={"class": "form-control"}),
            "bank_account_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        instance: Partner | None = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        # Label agar jelas (NPWP, legal, dll)
        if "tax" in self.fields:
            self.fields["tax"].label = "NPWP"
        if "name" in self.fields:
            self.fields["name"].label = "Nama / Brand (Short Name)"
        if "company_name" in self.fields:
            self.fields["company_name"].label = "Nama Legal (Billing)"

        # ===== GEO (sama konsep stabil) =====
        province_qs = Location.objects.filter(kind="province").order_by("name")
        self.fields["province"].widget.choices = \
            [("", "-- Pilih Provinsi --")] + list(province_qs.values_list("id", "name"))

        self.fields["regency"].widget.choices = [("", "-- Pilih Kab/Kota --")]
        self.fields["district"].widget.choices = [("", "-- Pilih Kecamatan --")]
        self.fields["village"].widget.choices = [("", "-- Pilih Kelurahan/Desa --")]

        def simple_choices(id_val):
            if not id_val:
                return [("", "---------")]
            qs = Location.objects.filter(pk=id_val).values_list("id", "name")
            return [("", "---------")] + list(qs)

        if instance:
            if instance.province_id:
                self.fields["province"].initial = instance.province_id
            if instance.regency_id:
                self.fields["regency"].widget.choices = simple_choices(instance.regency_id)
                self.fields["regency"].initial = instance.regency_id
            if instance.district_id:
                self.fields["district"].widget.choices = simple_choices(instance.district_id)
                self.fields["district"].initial = instance.district_id
            if instance.village_id:
                self.fields["village"].widget.choices = simple_choices(instance.village_id)
                self.fields["village"].initial = instance.village_id

        for f in [
            "province", "regency", "district", "village",
            "address_line1", "address_line2",
            "city", "post_code", "country",
            "bank_name", "bank_account",
            "sales_user",
            "company_type", "tax",
        ]:
            if f in self.fields:
                self.fields[f].required = False

    def clean(self):
        cleaned = super().clean()
        is_individual = bool(cleaned.get("is_individual"))
        name = (cleaned.get("name") or "").strip()
        company_name = (cleaned.get("company_name") or "").strip()

        if not name:
            self.add_error("name", "Nama/Brand wajib diisi.")
        if not is_individual and not company_name:
            self.add_error("company_name", "Nama legal (billing) wajib diisi untuk perusahaan.")

        if "company" in cleaned:
            cleaned["company"] = None

        return cleaned

    def save(self, commit=True):
        instance: Partner = super().save(commit=False)

        # simpan geo ke *_id
        for field in ["province", "regency", "district", "village"]:
            val = self.cleaned_data.get(field)
            setattr(instance, f"{field}_id", val if val else None)

        # vendor entity utama tidak punya induk
        if hasattr(instance, "company_id"):
            instance.company_id = None

        # personal vendor = contact sales+billing (kalau field ada)
        if getattr(instance, "is_individual", False):
            if hasattr(instance, "is_sales_contact"):
                instance.is_sales_contact = True
            if hasattr(instance, "is_billing_contact"):
                instance.is_billing_contact = True
        else:
            if hasattr(instance, "is_sales_contact"):
                instance.is_sales_contact = False
            if hasattr(instance, "is_billing_contact"):
                instance.is_billing_contact = False

        if commit:
            instance.save()

            # ✅ paksa role VENDOR
            role_type = get_vendor_role_type()
            PartnerRole.objects.get_or_create(partner=instance, role_type=role_type)

        return instance
