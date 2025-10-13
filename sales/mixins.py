# sales/views/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

def is_sales_user(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # sesuaikan: cek group/permission apa pun yang kamu pakai
    return user.groups.filter(name__in=["sales", "admin"]).exists() or user.has_perm("sales.view_salesquotation")

class SalesAccessRequiredMixin(LoginRequiredMixin):
    login_url = "account:login"

    def dispatch(self, request, *args, **kwargs):
        if not is_sales_user(request.user):
            raise PermissionDenied("Anda tidak berhak mengakses halaman Sales.")
        return super().dispatch(request, *args, **kwargs)
class UserToFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = getattr(self, "request", None) and self.request.user
        return kwargs
