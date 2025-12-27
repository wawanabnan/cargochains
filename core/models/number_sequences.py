from django.conf import settings
from django.db import models
from django.utils import timezone


        
class NumberSequence(models.Model):
    RESET_NONE = "none"
    RESET_MONTHLY = "monthly"
    RESET_YEARLY = "yearly"
    RESET_CHOICES = [
        (RESET_NONE, "None"),
        (RESET_MONTHLY, "Monthly"),
        (RESET_YEARLY, "Yearly"),
    ]

    app_label   = models.CharField(max_length=50)                   # "sales", "shipments", dst.
    code        = models.CharField(max_length=50)                   # "FREIGHT_QUOTATION", "FREIGHT_ORDER", dll.
    name = models.CharField(max_length=100, null=True, blank=True)  # sementara

    prefix      = models.CharField(max_length=20, blank=True, default="")  # "FQ", "SO", dll.
    format      = models.CharField(                                   # Template fleksibel
        max_length=120,
        default="{prefix}{year:04d}{month:02d}-{seq:05d}",
        help_text="Gunakan var: prefix, year, month, day (opsional), seq",
    )
    padding     = models.PositiveSmallIntegerField(default=5)        # fallback kalau format pakai {seq:0Nd}

    reset       = models.CharField(max_length=10, choices=RESET_CHOICES, default=RESET_MONTHLY)

    # State periode & counter terakhir
    last_number = models.PositiveIntegerField(default=0)
    period_year = models.PositiveSmallIntegerField(null=True, blank=True)
    period_month= models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "core_number_sequences" 
        constraints = [
            models.UniqueConstraint(fields=["app_label", "code"], name="uniq_sequence_per_app_code"),
        ]
        indexes = [
            models.Index(fields=["app_label", "code"]),
        ]

    def __str__(self):
        return f"{self.app_label}/{self.code} → {self.prefix} (reset={self.reset})"


