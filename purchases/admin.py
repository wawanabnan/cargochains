
from django.contrib import admin
from . import models as m

class PurchaseOrderLineInline(admin.TabularInline):
    model = m.PurchaseOrderLine
    extra = 0

@admin.register(m.PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "get_supplier_name", "order_date", "status", "currency", "total_amount", "created_at")
    list_filter = ("status", "currency", "order_date")
    search_fields = ("number", "ref_number", "supplier__partner__name")
    readonly_fields = ("number", "subtotal_amount", "tax_amount", "total_amount")
    inlines = [PurchaseOrderLineInline]

    def get_supplier_name(self, obj):
        return obj.supplier.partner.name if obj.supplier_id else "-"
    get_supplier_name.short_description = "Supplier"

@admin.register(m.PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = ("purchase_order", "line_no", "product_name", "uom", "qty", "unit_price", "line_discount")
    search_fields = ("number", "product_name", "description")
    list_filter = ("uom",)
