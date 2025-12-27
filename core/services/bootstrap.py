import secrets
import string

from django.conf import settings
from django.contrib.auth import get_user_model
from core.models.setup import SetupState


def _gen_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_initial_admin():
    User = get_user_model()
    if User.objects.exists():
        return

    state = SetupState.objects.first()
    if not state:
        state = SetupState.objects.create(is_completed=False, current_step=1)

    username = "admin"
    password = _gen_password(12)
    email = getattr(settings, "DEFAULT_FROM_EMAIL", "admin@example.com")

    user = User.objects.create_superuser(username=username, email=email, password=password)

    state.initial_admin_user_id = user.id
    state.initial_admin_username = username
    state.initial_admin_password = password
    state.force_password_change = True
    state.save()
