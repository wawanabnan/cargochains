
from django.contrib import admin
from . import models as m


@admin.register(m.ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")
    ordering = ("name",)


class ProjectCostInline(admin.TabularInline):
    model = m.ProjectCost
    extra = 0
    fields = ("category", "title", "amount", "currency_code", "cost_date", "notes")


@admin.register(m.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("number", "ref_number", "name", "category", "status", "start_date", "end_date", "created_at")
    list_filter = ("status", "category")
    search_fields = ("number", "ref_number", "name", "description")
    date_hierarchy = "start_date"
    readonly_fields = ("number",)
    inlines = [ProjectCostInline]


@admin.register(m.CostCategory)
class CostCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(m.ProjectCost)
class ProjectCostAdmin(admin.ModelAdmin):
    list_display = ("project", "category", "title", "amount", "currency_code", "cost_date", "created_at")
    list_filter = ("category", "currency_code")
    search_fields = ("project__number", "project__name", "title")
    autocomplete_fields = ("project", "category")
