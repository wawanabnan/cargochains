from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

# hanya import ini untuk logout GET
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
from django.http import HttpResponseRedirect

class UserLoginView(LoginView):
    template_name = "account/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("account:dashboard")

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "account/dashboard.html"
    login_url = reverse_lazy("account:login")

class LenientLogoutView(LogoutView):
    """Logout bisa via GET atau POST. GET dibebaskan dari CSRF."""
    next_page = reverse_lazy("account:login")

    http_method_names = ["get", "post", "head", "options"]  # pastikan GET diperbolehkan

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect(self.get_next_page())
# account/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.conf import settings

class UserLoginView(LoginView):
    template_name = "account/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("account:dashboard")

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "account/dashboard.html"
    login_url = reverse_lazy("account:login")

class LenientLogoutView(LogoutView):
    """Logout via GET atau POST; GET dibebaskan dari CSRF."""
    next_page = reverse_lazy("account:login")
    http_method_names = ["get", "post", "head", "options"]

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def _redirect_url(self, request):
        # urutan prioritas: explicit next_page -> ?next= -> settings.LOGOUT_REDIRECT_URL -> fallback ke login
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
        # biar POST juga tetap kerja normal
        logout(request)
        return HttpResponseRedirect(self._redirect_url(request))
