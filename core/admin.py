# core/admin.py
from django.contrib import admin
from .models import NumberSequence

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
        "app_label", "code", "prefix", "period_format",
        "period_year", "period_month", "last_no",
        "branch", "mode", "active",
    )
    list_filter = ("app_label", "code", "period_format", "branch", "mode", "active")
    search_fields = ("app_label", "code", "prefix", "branch", "mode")
    ordering = ("app_label", "code", "-period_year", "-period_month")
    actions = [reset_counter]

    # Susun field di form (buat created_at/updated_at di belakang)
    fields = (
        "active",
        "app_label", "code",
        "prefix", "period_format", "padding",
        "branch", "mode",
        "period_year", "period_month", "last_no",
        "created_at", "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")  # kalau pakai TimeStampedModel
