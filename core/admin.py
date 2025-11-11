# core/admin.py
from django.contrib import admin
from .models import (
    NumberSequence,
    CoreSetting,
    CompanyProfile,
    UOM,
    PaymentTerm,
    Currency,
    SalesService,
)


@admin.action(description="Reset counter (last_no=0, tetap periode sekarang)")
def reset_counter(modeladmin, request, queryset):
    updated = 0
    for seq in queryset:
        seq.last_no = 0
        seq.save(update_fields=["last_no"])
        updated += 1
    modeladmin.message_user(request, f"Reset {updated} sequence(s).")

@admin.register(NumberSequence)
class NumberSequenceAdmin(admin.ModelAdmin):
    list_display = (
        "app_label",
        "code",
        "name",
        "prefix",
        "format",        # jika field ini ada di model baru
        "reset",         # "none" | "monthly" | "yearly"
        "period_year",
        "period_month",
        "last_number",
        "padding",
    )

    search_fields = ("app_label", "code", "name", "prefix")

    # Hanya field yang benar-benar ada di model
    list_filter = (
        "app_label",
        "reset",
        "period_year",
        "period_month",
    )

    ordering = ("app_label", "code")

@admin.register(CoreSetting)
class CoreSettingAdmin(admin.ModelAdmin):
    list_display = ("code", "int_value", "char_value", "notes")
    search_fields = ("code",)

@admin.register(UOM)
class UOMdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "is_active")
    search_fields = ("code",)

@admin.register(PaymentTerm)
class PaymentTermdmin(admin.ModelAdmin):
    list_display = ("code", "name", "days", "description")
    search_fields = ("code",)
