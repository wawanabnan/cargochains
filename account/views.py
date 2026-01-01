# account/views.py

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView


class UserLoginView(LoginView):
    template_name = "account/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        """
        Prioritas:
        1) ?next= (default behavior Django LoginView)
        2) settings.LOGIN_REDIRECT_URL
        3) fallback ke dashboard account
        """
        url = self.get_redirect_url()
        if url:
            return url
        return resolve_url(getattr(settings, "LOGIN_REDIRECT_URL", None) or reverse_lazy("account:dashboard"))


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "account/dashboard.html"
    login_url = reverse_lazy("account:login")


class LenientLogoutView(LogoutView):
    """
    Logout via GET atau POST; GET dibebaskan dari CSRF.
    Redirect priority:
    - self.next_page (kalau diset)
    - ?next=
    - settings.LOGOUT_REDIRECT_URL
    - fallback ke login
    """
    next_page = reverse_lazy("account:login")
    http_method_names = ["get", "post", "head", "options"]

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def _redirect_url(self, request):
        target = (
            self.next_page
            or request.GET.get("next")
            or getattr(settings, "LOGOUT_REDIRECT_URL", None)
            or reverse_lazy("account:login")
        )
        return resolve_url(target)

    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect(self._redirect_url(request))

    def post(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect(self._redirect_url(request))
