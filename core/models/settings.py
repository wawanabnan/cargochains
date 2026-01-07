from django.conf import settings
from django.db import models
from django.utils import timezone


class CoreSetting(models.Model):

    CAT_SALES = "sales"
    CAT_FINANCE = "finance"
    CAT_OPERATION = "operation"

    CATEGORY_CHOICES = [
        (CAT_SALES, "Sales"),
        (CAT_FINANCE, "Finance"),
        (CAT_OPERATION, "Operation"),
    ]

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CAT_SALES,
        db_index=True
    )

    code = models.CharField(max_length=100, unique=True)
    int_value = models.IntegerField(null=True, blank=True)
    char_value = models.CharField(max_length=255, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")
    text_value = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "core_settings"

    def __str__(self):
        return f"{self.category}.{self.code}"
    
