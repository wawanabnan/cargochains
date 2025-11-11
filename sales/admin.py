# sales/admin.py
from django.contrib import admin, messages
from django.db import transaction
from django.utils.html import format_html

from .models import SalesQuotation, SalesOrder
from .auth import sales_queryset_for_user
from .signals import (
    _project_exists_for_line,
    _build_project_payload_for_line,
)
from projects.models import Project


@admin.register(SalesQuotation)
class SalesQuotationAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "customer", "valid_until", "sales_user", "status")
    list_filter  = ("status", "sales_user")
    search_fields = ("number", "customer__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("sales_user", "customer")
        return sales_queryset_for_user(qs, request.user)

    def save_model(self, request, obj, form, change):
        if not obj.sales_user_id:
            obj.sales_user = request.user
        super().save_model(request, obj, form, change)


# === Admin Action: Generate Project Now (per line) ===
@admin.action(description="Generate Project Now (per line)")
def action_generate_project(modeladmin, request, queryset):
    """
    Backfill manual:
    - Hanya untuk SalesOrder berstatus CONFIRMED
    - Buat Project per line jika belum ada (ref_number <SO>-L<line.id>)
    """
    created = 0
    skipped = 0
    with transaction.atomic():
        qs = (
            queryset
            .select_related("customer", "sales_user", "sales_service",
                            "sales_agency", "currency", "payment_term", "sales_quotation")
            .prefetch_related("lines__origin", "lines__destination")
        )
        for so in qs:
            if getattr(so, "status", "").upper() != "CONFIRMED":
                skipped += 1
                continue

            for line in so.lines.all():
                if _project_exists_for_line(so, line):
                    skipped += 1
                    continue
                payload = _build_project_payload_for_line(so, line)
                Project.objects.create(**payload)
                created += 1

    messages.success(request, f"Projects created: {created}, skipped: {skipped}")


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "customer", "sales_user", "status", "projects_info")
    list_filter  = ("status", "sales_user")
    search_fields = ("number", "customer__name")
    actions = [action_generate_project]

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .select_related("sales_user", "customer", "sales_service",
                            "sales_agency", "currency", "payment_term", "sales_quotation")
        )
        # untuk kolom projects_info kita akan query by ref_number, tidak perlu prefetch lagi di sini
        return sales_queryset_for_user(qs, request.user)

    def save_model(self, request, obj, form, change):
        if not obj.sales_user_id:
            obj.sales_user = request.user
        super().save_model(request, obj, form, change)

    def projects_info(self, obj: SalesOrder):
        """
        Tampilkan ringkas link ke semua Project yang terkait SO ini (berdasarkan pola ref_number).
        """
        # cari semua project ref_number yang diawali SO-number + "-L"
        projects = list(Project.objects.filter(ref_number__startswith=f"{obj.number}-L").only("pk", "number", "name"))
        if not projects:
            return "-"
        links = [
            f'<a href="/admin/projects/project/{p.pk}/change/">{p.number or p.name}</a>'
            for p in projects
        ]
        return format_html(", ".join(links))
    projects_info.short_description = "Projects"
