# shipments/admin.py
from django.contrib import admin
from .models import Shipment, ShipmentRoute, TransportationType, TransportationAsset


@admin.register(TransportationType)
class TransportationTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "mode")
    list_filter = ("mode",)
    search_fields = ("code", "name")


@admin.register(TransportationAsset)
class TransportationAssetAdmin(admin.ModelAdmin):
    list_display = ("identifier", "type", "carrier", "active")
    list_filter = ("active", "type__mode", "type")
    search_fields = ("identifier", "type__name", "carrier__name")


class ShipmentRouteInline(admin.TabularInline):
    model = ShipmentRoute
    extra = 0
    fields = (
        "order",
        "origin_text", "destination_text",
        "transportation_type", "transportation_type_text",
        "transportation_asset", "transportation_asset_text",
        "planned_departure", "planned_arrival",
        "actual_departure", "actual_arrival",
        "status",
    )
    readonly_fields = ("origin_text", "destination_text", "transportation_type_text", "transportation_asset_text")
    autocomplete_fields = ("origin", "destination", "transportation_type", "transportation_asset")
    ordering = ("order",)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        "number", "status", "origin_text", "destination_text",
        "booking_number", "bill_of_lading_no", "airwaybill_no",
        "mode", "service_level",
        "etd", "eta",
        "created_at",
    )
    list_filter = ("status", "mode", "service_level", "created_at")
    search_fields = ("number", "booking_number", "bill_of_lading_no", "airwaybill_no",
                     "origin_text", "destination_text",
                     "shipper__name", "consignee__name", "carrier__name")
    autocomplete_fields = ("origin", "destination", "shipper", "consignee", "carrier", "agency")
    inlines = [ShipmentRouteInline]
    readonly_fields = (
        "origin_text", "destination_text",
        "origin_snap", "destination_snap",
        "shipper_snap", "consignee_snap", "carrier_snap", "agency_snap",
        "created_at", "updated_at",
    )
    fieldsets = (
        ("Identifiers", {
            "fields": (
                ("number", "status"),
                ("so_number", "customer_reference"),
                ("booking_number",),
                ("bill_of_lading_no", "airwaybill_no"),
            )
        }),
        ("Locations", {
            "fields": (
                ("origin", "destination"),
                ("origin_text", "destination_text"),
                ("origin_snap", "destination_snap"),
            )
        }),
        ("Parties", {
            "fields": (
                ("shipper", "consignee"),
                ("carrier", "agency"),
                ("shipper_snap", "consignee_snap", "carrier_snap", "agency_snap"),
            )
        }),
        ("Cargo & Schedule", {
            "fields": (
                ("cargo_description",),
                ("weight", "volume", "qty", "package_type"),
                ("mode", "service_level", "inco_term"),
                ("vessel_name", "voyage_no", "flight_no"),
                ("etd", "eta", "atd", "ata"),
            )
        }),
        ("Financial", {
            "fields": (
                ("currency", "total"),
            )
        }),
        ("Audit", {
            "fields": (("created_at", "updated_at"),)
        }),
    )

@admin.action(description="Confirm selected shipments")
def action_confirm(modeladmin, request, queryset):
    from django.core.exceptions import ValidationError
    from shipments.services.transitions import confirm_shipment
    ok = 0
    for s in queryset:
        try:
            confirm_shipment(s, user=request.user); ok += 1
        except ValidationError: pass
    modeladmin.message_user(request, f"{ok} shipment confirmed.")

@admin.action(description="Book selected shipments (requires booking_number on each)")
def action_book(modeladmin, request, queryset):
    from django.core.exceptions import ValidationError
    from shipments.services.transitions import book_shipment
    ok = 0
    for s in queryset:
        try:
            book_shipment(s, user=request.user, booking_number=s.booking_number); ok += 1
        except ValidationError: pass
    modeladmin.message_user(request, f"{ok} shipment booked.")


class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("number","status","origin_text","destination_text","customer","carrier","created_at")
    search_fields = ("number","booking_number","bill_of_lading_no","airwaybill_no",
                     "origin_text","destination_text","customer__name","shipper__name","consignee__name","carrier__name")
    autocomplete_fields = ("origin","destination","customer","shipper","consignee","carrier","agency")
    fieldsets = (
        ("Identifiers", {...}),
        ("Parties", {
            "fields": (
                ("customer",),               # ← tambah ini
                ("shipper","consignee"),
                ("carrier","agency"),
                ("shipper_snap","consignee_snap","carrier_snap","agency_snap","customer_snap"),  # boleh readonly
            )
        }),
        ...
    )