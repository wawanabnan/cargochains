from django.contrib import admin
from .models import (
    SalesService, PaymentTerm, SalesNumberSequence,
    SalesQuotation, SalesQuotationLine,
    SalesOrder, SalesOrderLine
)

admin.site.register(SalesService)
admin.site.register(PaymentTerm)
admin.site.register(SalesNumberSequence)

class SalesQuotationLineInline(admin.TabularInline):
    model = SalesQuotationLine
    extra = 1

@admin.register(SalesQuotation)
class SalesQuotationAdmin(admin.ModelAdmin):
    list_display = ("id","number","customer_id","status","date","valid_until")
    search_fields = ("number",)
    list_filter = ("status","business_type")
    inlines = [SalesQuotationLineInline]


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    # ✅ pakai 'date' saja, bukan 'valid_until'
    list_display = (
        "number",
        "customer",
        "date",
        "sales_user_id",
        "currency",
#        "amount_total",
        "status",
        "updated_at",
    )
    list_filter = ("status", "business_type", "currency")
    search_fields = ("number", "customer__name")
    date_hierarchy = "date"

class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 1

