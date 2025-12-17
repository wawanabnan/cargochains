from django.contrib import admin

from .models import SalesTaxPolicy


@admin.register(SalesTaxPolicy)
class SalesTaxPolicyAdmin(admin.ModelAdmin):
    list_display = ("module", "tax", "is_active", "is_default")
    list_filter = ("module", "is_active", "is_default")
    search_fields = ("tax__code", "tax__name", "module")
    ordering = ("module", "tax__name")
