# core/models.py
from django.db import models

class TimeStampedModel(models.Model):
    """
    Abstract base class with created_at and updated_at timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class NumberSequence(TimeStampedModel):
    PERIOD_FORMAT_CHOICES = [
        ("NONE",   "None"),
        ("YYYY",   "YYYY"),
        ("YYYYMM", "YYYYMM"),
        ("MMYY",   "MMYY"),
    ]

    app_label     = models.CharField(max_length=50)              # "sales" / "ops"
    code          = models.CharField(max_length=50)              # "QUOTATION" / "ORDER" / "SHIPMENT"
    prefix        = models.CharField(max_length=30, blank=True, default="")  # "QO-" / "SO-" / "SH-SEA-"
    period_format = models.CharField(max_length=10, choices=PERIOD_FORMAT_CHOICES, default="MMYY")
    padding       = models.PositiveIntegerField(default=4)       # digit counter

    # state berjalan
    period_year   = models.PositiveIntegerField(default=0)
    period_month  = models.PositiveIntegerField(default=0)
    last_no       = models.PositiveIntegerField(default=0)

    # opsional pemecah counter
    branch        = models.CharField(max_length=10, blank=True, default="")
    mode          = models.CharField(max_length=10, blank=True, default="")  # "SEA"/"AIR"/"TRK" (opsional)

    active        = models.BooleanField(default=True)

    class Meta:
        db_table = "core_number_sequences"
        unique_together = [("app_label", "code", "branch", "mode")]

    def __str__(self):
        scope = "/".join([s for s in (self.app_label, self.code, self.branch, self.mode) if s])
        return f"{scope} [{self.prefix}{self.period_format}+{self.padding}]"
