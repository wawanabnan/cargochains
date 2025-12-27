from django.conf import settings
from django.db import models
from django.utils import timezone


class CoreSetting(models.Model):
    code = models.CharField(max_length=100, unique=True)
    int_value = models.IntegerField(null=True, blank=True)
    char_value = models.CharField(max_length=255, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "core_settings"

    def __str__(self):
        return f"{self.code}"
    
