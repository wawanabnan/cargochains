from django.contrib import admin
from .models import Partner, PartnerRole

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("id","name","email","phone","city","country")
    search_fields = ("name","email","phone","city","country")

