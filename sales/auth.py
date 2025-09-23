# sales/auth.py
from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

REQUIRED_PERM = "sales.access_sales"

def _has_sales_access(user):
    return user.is_authenticated and (user.is_superuser or user.has_perm(REQUIRED_PERM))

def sales_access_required(viewfunc):
    @wraps(viewfunc)
    @login_required(login_url="account:login")
    def _wrapped(request, *args, **kwargs):
        if _has_sales_access(request.user):
            return viewfunc(request, *args, **kwargs)
        return HttpResponseForbidden("Forbidden")
    return _wrapped

class SalesAccessRequiredMixin(LoginRequiredMixin):
    login_url = "account:login"
    required_permission = REQUIRED_PERM
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)  # biar redirect login dulu
        if request.user.is_superuser or request.user.has_perm(self.required_permission):
            return super().dispatch(request, *args, **kwargs)
        return HttpResponseForbidden("Forbidden")
