# shipments/models/sequence.py
from django.db import models

class ShipmentSequence(models.Model):
    yymm = models.CharField(max_length=4, unique=True)  # "2601"
    last_number = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.yymm}:{self.last_number}"
