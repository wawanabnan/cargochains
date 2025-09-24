# sales/admin.py
from django.contrib import admin
from .models import SalesQuotation, SalesOrder
from .auth import is_sales_supervisor, sales_queryset_for_user

@admin.register(SalesQuotation)
class SalesQuotationAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "customer", "valid_until", "sales_user", "status")
    list_filter  = ("status", "sales_user")
    search_fields = ("number", "customer__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("sales_user")
        # Batasi admin juga: sales biasa hanya lihat miliknya
        return sales_queryset_for_user(qs, request.user)

    def save_model(self, request, obj, form, change):
        if not obj.sales_user_id:
            obj.sales_user = request.user
        super().save_model(request, obj, form, change)

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "customer", "sales_user", "status")
    list_filter  = ("status", "sales_user")
    search_fields = ("number", "customer__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("sales_user")
        return sales_queryset_for_user(qs, request.user)

    def save_model(self, request, obj, form, change):
        if not obj.sales_user_id:
            obj.sales_user = request.user
        super().save_model(request, obj, form, change)
