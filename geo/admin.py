from django.contrib import admin
from .models import Location

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id","code","name","kind","parent")
    list_filter = ("kind",)
    search_fields = ("code","name")
