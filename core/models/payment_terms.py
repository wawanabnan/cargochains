from django.conf import settings
from django.db import models
from django.utils import timezone

class PaymentTerm(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    days = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        db_table = "payment_terms"
        ordering = ["name"]

    def __str__(self):
        return self.name
