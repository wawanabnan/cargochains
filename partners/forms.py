# partners/forms.py
from django import forms
from geo.models import Location
from .models import Partner, PartnerRoleTypes, PartnerRole


class PartnerForm(forms.ModelForm):
    # Roles (multi checkbox)
    roles = forms.ModelMultipleChoiceField(
        queryset=PartnerRoleTypes.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Roles",
    )

    # --- 4 FIELD GEO buatan kita sendiri ---
    # BUKAN ModelChoiceField, hanya integer untuk ambil id
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
        # Penting: form TIDAK menggunakan FK model untuk geo & location.
        exclude = ["province", "regency", "district", "village", "location"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "websites": forms.TextInput(attrs={"class": "form-control"}),

            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_type": forms.Select(attrs={"class": "form-select"}),
            "tax": forms.TextInput(attrs={"class": "form-control"}),

            "post_code": forms.TextInput(attrs={"class": "form-control"}),
            "address_line1": forms.TextInput(attrs={"class": "form-control"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control"}),

            "is_individual": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_pkp": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "country": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "sales_user": forms.Select(attrs={"class": "form-select"}),
            "company": forms.Select(attrs={"class": "form-select"}),

        }

    def __init__(self, *args, **kwargs):
        instance: Partner | None = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        # ---------
        # LABEL NPWP
        # ---------
        if "tax" in self.fields:
            self.fields["tax"].label = "NPWP"

        # ---------
        # ROLES (EDIT)
        # ---------
        if instance and instance.pk:
            self.fields["roles"].initial = (
                PartnerRole.objects.filter(partner=instance)
                .values_list("role_type_id", flat=True)
            )

        if "company" in self.fields:
            self.fields["company"].queryset = Partner.objects.filter(
                is_individual=False
            ).order_by("company_name", "name")
            self.fields["company"].required = False

        # ----------------
        # GEO — VERSI RINGAN
        # ----------------
        # Province — load 38 row
        province_qs = Location.objects.filter(kind="province").order_by("name")
        self.fields["province"].widget.choices = \
            [("", "-- Pilih Provinsi --")] + list(province_qs.values_list("id", "name"))

        # Regency/district/village default kosong (Add)
        self.fields["regency"].widget.choices = [("", "-- Pilih Kab/Kota --")]
        self.fields["district"].widget.choices = [("", "-- Pilih Kecamatan --")]
        self.fields["village"].widget.choices = [("", "-- Pilih Kelurahan/Desa --")]

        # EDIT → isi initial dropdown dengan 1 pilihan (yang sedang digunakan)
        def simple_choices(id_val):
            if not id_val:
                return [("", "---------")]
            qs = Location.objects.filter(pk=id_val).values_list("id", "name")
            return [("", "---------")] + list(qs)

        if instance:
            # Province
            if instance.province_id:
                self.fields["province"].initial = instance.province_id

            # Regency
            if instance.regency_id:
                self.fields["regency"].widget.choices = simple_choices(instance.regency_id)
                self.fields["regency"].initial = instance.regency_id

            # District
            if instance.district_id:
                self.fields["district"].widget.choices = simple_choices(instance.district_id)
                self.fields["district"].initial = instance.district_id

            # Village
            if instance.village_id:
                self.fields["village"].widget.choices = simple_choices(instance.village_id)
                self.fields["village"].initial = instance.village_id

        # Semua alamat tidak wajib diisi
        for f in [
            "province", "regency", "district", "village",
            "address_line1", "address_line2",
            "city", "post_code", "country",
        ]:
            self.fields[f].required = False

    def clean(self):
        cleaned_data = super().clean()
        is_individual = cleaned_data.get("is_individual")
        company = cleaned_data.get("company")

        # Kalau contact person (individu) → wajib punya perusahaan induk
        if is_individual and not company:
            self.add_error(
                "company",
                "Pilih perusahaan induk untuk contact person ini.",
            )

        return cleaned_data

    # -------------------
    # SAVE — STABIL & SIMPLE
    # -------------------
    def save(self, commit=True):
        instance: Partner = super().save(commit=False)

        # SIMPAN GEO langsung ke *_id
        for field in ["province", "regency", "district", "village"]:
            val = self.cleaned_data.get(field)
            setattr(instance, f"{field}_id", val if val else None)

        if commit:
            instance.save()

            # SIMPAN ROLES
            roles = self.cleaned_data.get("roles")
            if roles is not None:
                PartnerRole.objects.filter(partner=instance)\
                    .exclude(role_type__in=roles).delete()
                for r in roles:
                    PartnerRole.objects.get_or_create(
                        partner=instance, role_type=r
                    )

        return instance
