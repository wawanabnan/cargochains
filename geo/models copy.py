from django.db import models

class Location(models.Model):
    code = models.CharField(max_length=20,unique=True, blank=False, null=False)
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "locations"
        indexes = [
            #models.Index(fields=["code"], name="loc_code_idx"),
            models.Index(fields=["kind"], name="loc_kind_idx"),
            models.Index(fields=["parent"], name="loc_parent_idx"),
            models.Index(fields=["name"], name="loc_name_idx"),
            models.Index(fields=["iata_code"], name="loc_iata_idx"),
            models.Index(fields=["unlocode"], name="loc_unlocode_idx"),
        ]

    def __str__(self): return f"{self.name} [{self.kind}]"
    def save(self, *args, **kwargs):
        if not self.code:
            base = (self.unlocode or self.iata_code or slugify(self.name) or "LOC").upper()
            base = base[:20]  # jaga panjang
            code = base
            i = 1
            while Location.objects.filter(code=code).exclude(pk=self.pk).exists():
                # tambahkan suffix numerik, tetap <=20 char
                suffix = f"-{i}"
                code = (base[: (20 - len(suffix))] + suffix)
                i += 1
            self.code = code
        super().save(*args, **kwargs)