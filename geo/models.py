from django.db import models
from core.models import TimeStampedModel

class Location(TimeStampedModel):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20)  # country/province/city/seaport/airport/...
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                               db_column="parent_id", related_name="children")
    lft = models.IntegerField(null=True, blank=True)
    rght = models.IntegerField(null=True, blank=True)
    iata_code = models.CharField(max_length=10, null=True, blank=True)
    unlocode  = models.CharField(max_length=10, null=True, blank=True)
    latitude  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    class Meta:
        db_table = "locations"
        indexes = [
            models.Index(fields=["code"], name="loc_code_idx"),
            models.Index(fields=["kind"], name="loc_kind_idx"),
            models.Index(fields=["parent"], name="loc_parent_idx"),
        ]

    def __str__(self): return f"{self.name} [{self.kind}]"
