import uuid
from django.db import models

class SetupState(models.Model):
    is_completed = models.BooleanField(default=False)
    current_step = models.PositiveIntegerField(default=1)
    setup_token = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_setup_state"

    def ensure_token(self):
        if not self.setup_token:
            self.setup_token = uuid.uuid4().hex
            self.save(update_fields=["setup_token"])
        return self.setup_token
