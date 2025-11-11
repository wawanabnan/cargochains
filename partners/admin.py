from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import Partner, PartnerRole, PartnerRoleTypes


# partners/admin.py

class PartnerAdminForm(forms.ModelForm):
    roles = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=PartnerRoleTypes.objects.filter(is_active=True),
        required=False,
        widget=FilteredSelectMultiple("Role Types", is_stacked=False),
        help_text="Pilih satu atau lebih role untuk partner ini."
    )

    class Meta:
        model = Partner
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # isi initial dari relasi PartnerRole yg ada
        if self.instance and self.instance.pk:
            current_ids = (PartnerRole.objects
                           .filter(partner=self.instance)
                           .values_list("role_type_id", flat=True))
            self.fields["roles"].initial = list(current_ids)

    def save(self, commit=True):
        obj = super().save(commit=commit)
        # sinkronisasi PartnerRole setelah Partner tersimpan
        def sync_roles():
            chosen = set(self.cleaned_data.get("roles").values_list("id", flat=True)) if self.cleaned_data.get("roles") else set()
            existing = set(PartnerRole.objects.filter(partner=obj).values_list("role_type_id", flat=True))

            to_add = chosen - existing
            to_del = existing - chosen

            if to_add:
                PartnerRole.objects.bulk_create([
                    PartnerRole(partner=obj, role_type_id=rid) for rid in to_add
                ])
            if to_del:
                PartnerRole.objects.filter(partner=obj, role_type_id__in=to_del).delete()

        # kalau commit False, tanggung jawab caller; kalau True, langsung sinkron
        if commit and self.is_valid():
            sync_roles()
        else:
            # simpan fungsi untuk dipanggil di save_related
            self._sync_roles = sync_roles
        return obj

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    form = PartnerAdminForm
    list_display  = (
        "name", "company_name", "company_type",
        "is_individual", "is_pkp", "roles_display", "sales_user"
    )
    search_fields = ("name", "company_name", "email", "phone", "mobile", "tax")
    list_filter   = ("company_type", "is_individual", "is_pkp", "sales_user")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # jalankan sinkron jika ditunda di form.save(commit=False)
        sync_fn = getattr(form, "_sync_roles", None)
        if callable(sync_fn):
            sync_fn()

    def roles_display(self, obj):
        qs = (PartnerRole.objects
              .filter(partner=obj)
              .select_related("role_type")
              .values_list("role_type__name", flat=True))
        names = sorted(set(qs))
        return ", ".join(names) if names else "-"
    roles_display.short_description = "Roles"


# ======== MENU TERPISAH: Partner Role Types ========
@admin.register(PartnerRoleTypes)
class PartnerRoleTypesAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    ordering = ("name",)


# ======== MENU TERPISAH: Partner Roles (opsional) ========
# Kalau kamu ingin bisa kelola tabel penghubungnya langsung dari menu:
@admin.register(PartnerRole)
class PartnerRoleAdmin(admin.ModelAdmin):
    list_display = ("partner", "role_type", "created_at")
    search_fields = ("partner__name", "role_type__name")
    autocomplete_fields = ("partner", "role_type")
    list_filter = ("role_type",)
    ordering = ("-created_at",)