
from django.contrib import admin
from .models import Shipment, ShipmentRoute, ShipmentDocument, ShipmentStatusLog, TransportationType

class ShipmentRouteInline(admin.TabularInline):
    model = ShipmentRoute
    extra = 1

class ShipmentDocumentInline(admin.TabularInline):
    model = ShipmentDocument
    extra = 1

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "status", "origin", "destination", "etd", "eta", "created_at")
    list_filter = ("status",)
    search_fields = ("number", "bill_of_lading_no")
    inlines = [ShipmentRouteInline, ShipmentDocumentInline]

@admin.register(TransportationType)
class TransportationTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "transportation_mode", "created_at")

@admin.register(ShipmentStatusLog)
class ShipmentStatusLogAdmin(admin.ModelAdmin):
    list_display = ("id", "shipment", "status", "event_time", "user", "recorded_at")

@admin.register(ShipmentDocument)
class ShipmentDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "shipment", "doc_type", "file_path", "created_at")

@admin.register(ShipmentRoute)
class ShipmentRouteAdmin(admin.ModelAdmin):
    list_display = ("id", "shipment", "origin", "destination", "transportation_type", "created_at")
