from functools import wraps
from django.shortcuts import redirect
from core.models.setup import SetupState

def require_setup_session(viewfunc):
    @wraps(viewfunc)
    def _wrapped(request, *args, **kwargs):
        state = SetupState.objects.first()
        if state and state.is_completed:
            return redirect("/account/login/")

        if not request.session.get("setup_mode") or not request.session.get("setup_admin_user_id"):
            return redirect("/welcome/?err=setup_requires_admin")
        return viewfunc(request, *args, **kwargs)
    return _wrapped
