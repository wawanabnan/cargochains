from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.services.setup import get_setup_state


class InitialSetupMiddleware(MiddlewareMixin):
    """
    Jika setup belum completed, user akan diarahkan ke wizard.
    Wizard tidak mengganggu halaman login/logout/static/media.
    """

    EXEMPT_PREFIXES = (
        "/admin/",
        "/accounts/",
        "/static/",
        "/media/",
    )

    def process_request(self, request):
        path = request.path or "/"

        # skip exempt paths
        for p in self.EXEMPT_PREFIXES:
            if path.startswith(p):
                return None

        # skip setup paths themselves
        if path.startswith("/setup/"):
            return None

        # kalau belum login, biarkan flow auth normal
        if not request.user.is_authenticated:
            return None

        state = get_setup_state()
        if not state.is_completed:
            return redirect(reverse("core:setup_step", kwargs={"step": state.current_step}))
        return None
