import secrets
import string

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from core.models.setup import SetupState


def _gen_password(length=12):
    alphabet = string.ascii_letters + string.digits
    # boleh tambah simbol kalau mau: + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@receiver(post_migrate)
def ensure_initial_admin(sender, **kwargs):
    """
    Create initial admin automatically if no users exist.
    Runs after migrations.
    """
    # Hanya jalan untuk app core (biar tidak kepanggil berkali-kali dari app lain)
    if sender.name != "core":
        return

    User = get_user_model()

    # kalau sudah ada user, jangan buat apa-apa
    if User.objects.exists():
        return

    # pastikan SetupState ada
    state = SetupState.objects.first()
    if not state:
        state = SetupState.objects.create(is_completed=False, current_step=1)

    # generate admin
    username = "admin"
    password = _gen_password(12)
    email = getattr(settings, "DEFAULT_FROM_EMAIL", "admin@example.com")

    user = User.objects.create_superuser(username=username, email=email, password=password)

    state.initial_admin_user_id = user.id
    state.initial_admin_username = username
    state.initial_admin_password = password
    state.force_password_change = True
    state.save(update_fields=[
        "initial_admin_user_id",
        "initial_admin_username",
        "initial_admin_password",
        "force_password_change",
        "updated_at",
    ])
