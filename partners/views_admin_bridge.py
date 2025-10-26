from django.contrib import admin
from django.http import Http404
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse
from .models import Partner

# Dekorator: pakai admin login + next
def staff_required(viewfunc):
    return user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url="/admin/login/"  # penting: pakai login admin
    )(viewfunc)

def _get_ma(model):
    try:
        return admin.site._registry[model]
    except KeyError:
        raise Http404("Model belum terdaftar di Django Admin.")

@staff_required
def customers_admin_list(request):
    ma = _get_ma(Partner)
    # tampilkan changelist admin di URL custom-mu (tanpa redirect ke /admin/)
    return admin.site.admin_view(ma.changelist_view)(request)

@staff_required
def customers_admin_add(request):
    ma = _get_ma(Partner)
    return admin.site.admin_view(ma.add_view)(request)

@staff_required
def customers_admin_change(request, object_id):
    ma = _get_ma(Partner)
    return admin.site.admin_view(ma.change_view)(request, object_id=object_id)

# (opsional) helper: langsung filter hanya "Customer"
@staff_required
def customers_only(request):
    url = reverse("partners:customers_admin_list") + "?role__exact=CUSTOMER"
    return redirect(url)
