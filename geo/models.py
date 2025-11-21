from django.db import models
from django.utils.text import slugify
from django.db.models import Q
from django.core.exceptions import ValidationError


try:
    from django.contrib.gis.db import models as gis_models
    from django.contrib.gis.geos import Point
    GEO_ENABLED = True
except Exception:
    gis_models = None
    Point = None
    GEO_ENABLED = False

class LocationKind(models.TextChoices):
    KIND_COUNTRY   = "country"
    KIND_PROVINCE  = "province"
    KIND_REGENCY   = "regency"
    KIND_CITY_ADMIN= "city-admin"
    KIND_DISTRICT  = "district"
    KIND_LOCALITY  = "locality"
    KIND_CITY      = "city"
    KIND_AIRPORT   = "airport"
    KIND_PORT      = "port"
    KIND_JETTY     = "jetty"
    KIND_ANCHORAGE = "anchorage"


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

    # === TAMBAHAN BARU (kompatibel & opsional) ===
    display_name = models.CharField(max_length=255, null=True, blank=True)
    country_code = models.CharField(max_length=2, null=True, blank=True)  # ISO 3166-1 alpha2
    iso_code = models.CharField(max_length=20, null=True, blank=True)     # ISO 3166-2
    altitude = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(
        max_length=8,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )
    source = models.CharField(max_length=100, null=True, blank=True)
    note = models.TextField(null=True, blank=True)

     # Geo opsional
    if GEO_ENABLED:
        geom = gis_models.PointField(srid=4326, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "locations"
        indexes = [
            #models.Index(fields=["code"], name="loc_code_idx"),
            models.Index(fields=["code"], name="loc_code_idx"),
            models.Index(fields=["kind"], name="loc_kind_idx"),
            models.Index(fields=["parent"], name="loc_parent_idx"),
            models.Index(fields=["name"], name="loc_name_idx"),
            models.Index(fields=["iata_code"], name="loc_iata_idx"),
            models.Index(fields=["unlocode"], name="loc_unlocode_idx"),
            models.Index(fields=["parent", "kind"], name="loc_parent_kind_idx"),
            models.Index(fields=["kind", "name"], name="loc_kind_name_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(latitude__isnull=True) | (Q(latitude__gte=-90) & Q(latitude__lte=90)),
                name="chk_lat_range",
            ),
            models.CheckConstraint(
                check=Q(longitude__isnull=True) | (Q(longitude__gte=-180) & Q(longitude__lte=180)),
                name="chk_lng_range",
            ),
        ]

    def clean(self):
        # parent tidak boleh dirinya sendiri
        if self.pk and self.parent_id and self.parent_id == self.pk:
            raise ValidationError("Parent Location tidak boleh dirinya sendiri.")

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


        if not self.display_name:
            self.display_name = self.name

        # tambahan aman: sync geom jika GeoDjango aktif
        if GEO_ENABLED and self.latitude is not None and self.longitude is not None:
            try:
                self.geom = Point(float(self.longitude), float(self.latitude), srid=4326)
            except Exception:
                pass

        super().save(*args, **kwargs)


    @property
    def full_path(self):
        """Kembalikan path hierarkis, mis: Indonesia > Kalimantan Timur > Berau > Muara Berau"""
        parts = [self.name]
        p = self.parent
        while p:
            parts.append(p.name)
            p = p.parent
        return " > ".join(reversed(parts))

    def ancestors(self):
        """Daftar parent dari atas ke bawah."""
        out, p = [], self.parent
        while p:
            out.append(p)
            p = p.parent
        return list(reversed(out))
    
    def root(self):
        """Ambil parent tertinggi."""
        p = self
        while p.parent_id:
            p = p.parent
        return p

    def siblings(self, include_self=False):
        """Saudara satu parent."""
        qs = Location.objects.filter(parent_id=self.parent_id)
        return qs if include_self else qs.exclude(id=self.id)

    def is_airport(self):
        return (self.kind or "").lower() == "airport"

    def is_port(self):
        return (self.kind or "").lower() in ("port", "seaport")

    def set_coords(self, lat, lng, commit=True):
        """Set latitude/longitude dengan aman (dan geom bila aktif)."""
        self.latitude = lat
        self.longitude = lng
        if GEO_ENABLED and lat is not None and lng is not None:
            try:
                self.geom = Point(float(lng), float(lat), srid=4326)
            except Exception:
                pass
        if commit:
            self.save(update_fields=["latitude", "longitude"] + (["geom"] if GEO_ENABLED else []))
