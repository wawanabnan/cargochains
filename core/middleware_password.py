from django.shortcuts import redirect
from django.urls import reverse
from core.models.setup import SetupState


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # skip kalau belum login
        if not request.user.is_authenticated:
            return self.get_response(request)

        state = SetupState.objects.first()
        if not state:
            return self.get_response(request)

        # hanya paksa untuk initial admin & flag masih aktif
        if (
            state.force_password_change
            and state.initial_admin_user_id
            and request.user.id == state.initial_admin_user_id
        ):
            path = request.path or ""

            # allow these paths
            allow_prefixes = (
                "/accounts/password/change/",
                "/accounts/logout/",
                "/setup/",
                "/admin/",
                "/static/",
                "/media/",
            )
            if not path.startswith(allow_prefixes):
                return redirect(reverse("core:password_change_required"))

        return self.get_response(request)
