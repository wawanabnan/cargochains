from functools import wraps
from django.http import HttpResponseForbidden

def role_required(*roles):
    def deco(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Forbidden")
            prof = getattr(request.user, "userprofile", None)
            if prof is None or (roles and prof.role not in roles):
                return HttpResponseForbidden("Forbidden")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return deco
    