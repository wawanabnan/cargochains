# sales/auth.py
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

# ---- supervisor / akses luas ----
def is_sales_supervisor(user):
    """
    True jika superuser atau anggota group 'Sales Supervisor'.
    Group opsional: kalau tidak dipakai, tetap True untuk superuser saja.
    """
    if not user or not user.is_authenticated:
        return False
    try:
        return user.is_superuser or user.groups.filter(name__iexact="Sales Supervisor").exists()
    except Exception:
        return getattr(user, "is_superuser", False)

def can_view_all_sales(user):
    """
    True jika boleh melihat SEMUA data sales:
    - superuser, atau
    - punya permission 'sales.view_all_sales', atau
    - (opsional) anggota grup 'Sales Supervisor'
    """
    return (
        getattr(user, "is_superuser", False)
        or (user.is_authenticated and user.has_perm("sales.view_all_sales"))
        or is_sales_supervisor(user)
    )

# ---- filter queryset per user ----
def sales_queryset_for_user(qs, user, include_null=False):
    """
    Supervisor/role-izin: lihat semua.
    User biasa: hanya miliknya (mendeteksi field kepemilikan secara dinamis).
    Prioritas field: sales_user > salesperson > created_by
    include_null=True => ikutkan record lama yang fieldnya NULL (opsional).
    """
    if not user or not user.is_authenticated:
        return qs.none()

    if can_view_all_sales(user):
        return qs

    field_names = {f.name for f in qs.model._meta.get_fields()}

    if "sales_user" in field_names:
        cond = Q(sales_user=user)
        if include_null:
            cond |= Q(sales_user__isnull=True)
        return qs.filter(cond)

    if "salesperson" in field_names:  # fallback untuk model lama yang masih pakai nama ini
        cond = Q(salesperson=user)
        if include_null:
            cond |= Q(salesperson__isnull=True)
        return qs.filter(cond)

    if "created_by" in field_names:
        return qs.filter(created_by=user)

    # kalau tidak ada field kepemilikan yang dikenal, ketat saja
    return qs.none()

# ---- (opsional) dekorator & mixin akses modul ----
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

def sales_access_required(viewfunc):
    """
    Wajib login + wajib punya akses modul sales:
    - 'sales.access_sales' ATAU can_view_all_sales(user)
    """
    @wraps(viewfunc)
    @login_required
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if u.has_perm("sales.access_sales") or can_view_all_sales(u):
            return viewfunc(request, *args, **kwargs)
        raise PermissionDenied("Tidak punya akses ke Sales module.")
    return _wrapped


class SalesAccessRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Mixin untuk CBV:
    - Wajib login
    - Boleh akses jika:
      * superuser, atau
      * punya permission 'sales.view_all_sales', atau
      * anggota grup 'Sales Supervisor' (opsional via is_sales_supervisor), atau
      * punya permission 'sales.access_sales'
    """
    permission_required = ("sales.access_sales",)
    raise_exception = True  # biar 403 (PermissionDenied) daripada redirect

    def has_permission(self):
        u = self.request.user
        # izinkan jika punya akses luas
        try:
            from .auth import can_view_all_sales  # jika fungsi ada di file yang sama, import tidak wajib
        except Exception:
            def can_view_all_sales(_u):  # fallback aman
                return getattr(_u, "is_superuser", False)
        return can_view_all_sales(u) or super().has_permission()
    