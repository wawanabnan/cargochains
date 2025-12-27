from django.db import models
from .chart import Account


class AccountingPeriodLock(models.Model):

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()  # 1..12
    is_locked = models.BooleanField(default=True)

    locked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.year}-{self.month:02d} ({'LOCKED' if self.is_locked else 'OPEN'})"
