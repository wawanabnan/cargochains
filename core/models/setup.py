from django.db import models

class SetupState(models.Model):
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_step = models.PositiveSmallIntegerField(default=1)

    # === Initial admin bootstrap ===
    initial_admin_user_id = models.IntegerField(null=True, blank=True)
    initial_admin_username = models.CharField(max_length=150, null=True, blank=True)

    # tampilkan hanya sekali (dan nanti dihapus setelah password diganti)
    initial_admin_password = models.CharField(max_length=128, null=True, blank=True)

    # paksa user itu ganti password
    force_password_change = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_setup_state"
