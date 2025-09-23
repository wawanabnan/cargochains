# account/middleware.py
from django.conf import settings
from django.shortcuts import redirect
from urllib.parse import quote

EXEMPT_PREFIXES = (
    "/account/login/",
    "/account/logout/",
    "/admin/",          # biar bisa akses /admin login
    "/__debug__/",      # jika pakai debug toolbar
)

def _is_exempt(path: str) -> bool:
    # Bebaskan static & media
    static_url = getattr(settings, "STATIC_URL", "/static/")
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    if static_url and path.startswith(static_url):
        return True
    if media_url and path.startswith(media_url):
        return True
    # Bebaskan prefix lain
    return any(path.startswith(p) for p in EXEMPT_PREFIXES)

class LoginRequiredMiddleware:
    """Paksa semua request (kecuali exempt) hanya untuk user yang sudah login."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user = getattr(request, "user", None)

        if not _is_exempt(path):
            if not (user and user.is_authenticated):
                # redirect ke LOGIN_URL dengan ?next=<path>
                login_url = settings.LOGIN_URL if isinstance(settings.LOGIN_URL, str) else "/account/login/"
                return redirect(f"{login_url}?next={quote(path)}")

        return self.get_response(request)
