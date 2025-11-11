# sales/access.py
from functools import wraps
from django.contrib import admin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q

# === KONSTANTA IZIN & GRUP (ubah jika perlu) ===
PERM_ACCESS  = "sales.access_sales"      # izin: boleh akses modul sales
PERM_VIEWALL = "sales.view_all_sales"    # izin: boleh lihat semua data sales
GROUP_SUPERV = "Sales Supervisor"        # opsional: nama group supervisor

# === UTIL: siapa supervisor / siapa boleh lihat semua ===
def is_supervisor(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or user.groups.filter(name__iexact=GROUP_SUPERV).exists()

def can_view_all(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or user.has_perm(PERM_VIEWALL) or is_supervisor(user)

# === FILTER QUERYSET BERDASAR USER (object-level) ===
def sales_queryset_for_user(qs, user, include_null=False):
    """
    Supervisor (view_all) → semua data.
    Selain itu → hanya data milik user, deteksi field kepemilikan secara dinamis.
    Prioritas field: sales_user > salesperson > created_by.
    """
    if not getattr(user, "is_authenticated", False):
        return qs.none()
    if can_view_all(user):
        return qs

    field_names = {f.name for f in qs.model._meta.get_fields()}
    for owner_field in ("sales_user", "salesperson", "created_by"):
        if owner_field in field_names:
            cond = Q(**{owner_field: user})
            if include_null:
                cond |= Q(**{f"{owner_field}__isnull": True})
            return qs.filter(cond)
    return qs.none()

# === DEKORATOR UNTUK FBV ===
def sales_access_required(viewfunc):
    """
    Pakai di FBV: wajib login + punya access_sales (atau supervisor/view_all).
    """
    @wraps(viewfunc)
    @login_required
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if u.has_perm(PERM_ACCESS) or can_view_all(u):
            return viewfunc(request, *args, **kwargs)
        raise PermissionDenied("Tidak punya akses ke Sales.")
    return _wrapped

def perm_required_access(raise_exc=True):
    """
    Alternatif ringkas: @perm_required_access() -> cek 'sales.access_sales'.
    """
    return permission_required(PERM_ACCESS, raise_exception=raise_exc)

# === MIXIN UNTUK CBV (views) ===
class SalesAccessRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Wajib login + punya 'sales.access_sales' atau privilege supervisor/view_all.
    """
    permission_required = (PERM_ACCESS,)
    raise_exception = True  # 403 daripada redirect ke login

    def has_permission(self):
        return can_view_all(self.request.user) or super().has_permission()

class SalesOwnedQuerysetMixin:
    """
    Campurkan ke ListView/DetailView/DRF ViewSet:
      def get_queryset(self):
          return self.get_filtered_queryset(super().get_queryset())
    """
    include_null_ownership = True

    def get_filtered_queryset(self, qs):
        return sales_queryset_for_user(qs, self.request.user, include_null=self.include_null_ownership)

# === BASE ADMIN: batasi data milik sendiri di Django Admin ===
class SalesOwnedOnlyAdmin(admin.ModelAdmin):
    """
    Pakai sebagai base class ModelAdmin untuk modul sales:
    - Supervisor / user dengan PERM_VIEWALL → lihat semua
    - Lainnya → hanya record miliknya (sales_user / salesperson / created_by)
    Serta auto-isi owner saat create jika fieldnya tersedia & masih kosong.
    """
    include_null_ownership = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return sales_queryset_for_user(qs, request.user, include_null=self.include_null_ownership)

    def save_model(self, request, obj, form, change):
        # Auto-assign owner jika ada field kepemilikan & belum terisi
        for owner_field in ("sales_user", "salesperson", "created_by"):
            if hasattr(obj, owner_field) and getattr(obj, owner_field, None) is None:
                setattr(obj, owner_field, request.user)
                break
        super().save_model(request, obj, form, change)
