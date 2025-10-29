# shipments/models.py
from django.db import models
from django.db.models import Q, CheckConstraint, F
from geo.models import Location
from partners.models import Partner

class Shipment(models.Model):

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),   # setelah sales melengkapi data
        ('BOOKED', 'Booked'),         # setelah daftar ke carrier (punya booking number)
        ('IN_TRANSIT', 'In Transit'),
        ('ARRIVED', 'Arrived'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)

    # Audit status shifts
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='confirmed_shipments')
    booked_at    = models.DateTimeField(null=True, blank=True)
    booked_by    = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='booked_shipments')
    
    #
    # --- Identifiers ---
    number = models.CharField(max_length=30, unique=True, db_index=True)   # internal running number
    sales_order = models.ForeignKey('sales.SalesOrder', on_delete=models.PROTECT,  # atau SET_NULL kalau mau bisa dihapus
        null=True, blank=True, related_name='shipments', db_column='sales_order_id'
    )
    so_number = models.CharField(max_length=30, null=True, blank=True)     # sales order/customer order (opsional)
    sales_order_snap = models.JSONField(null=True, blank=True)  # snapshot ringan (customer, nilai, dll.)

    @property
    def sales_order_number(self):
        return self.so_number or (self.sales_order.number if self.sales_order_id else "-")

    
    @property
    def customer_name(self):
        # prioritas: FK customer pada shipment, kalau kosong ambil dari SO
        if getattr(self, "customer_id", None):
            return self.customer.name
        if self.sales_order_id and getattr(self.sales_order, "customer", None):
            return self.sales_order.customer.name
        snap = self.sales_order_snap or {}
        return snap.get("customer_name") or "-"

    @property
    def booking_ref(self):
        so = getattr(self, "sales_order", None)
        if so:
            return getattr(so, "booking_number", None) or getattr(so, "number", None)
        return getattr(self, "so_number", None)

    # Booking dari carrier (CNTR/Flight/Vessel booking no). Diterbitkan carrier saat confirm.
    booking_number = models.CharField(max_length=50, blank=True, db_index=True)

    # BL/AWB (dokumen akhir dari carrier)
    bill_of_lading_no = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    airwaybill_no = models.CharField(max_length=50, null=True, blank=True, db_index=True)

    # --- Lokasi header (origin/destination keseluruhan) ---
    origin = models.ForeignKey(
        Location, on_delete=models.PROTECT,
        related_name='shipment_origins', db_column='origin_id'
    )
    destination = models.ForeignKey(
        Location, on_delete=models.PROTECT,
        related_name='shipment_destinations', db_column='destination_id'
    )
    origin_text = models.CharField(max_length=100, null=True, blank=True, db_column='origin')
    destination_text = models.CharField(max_length=100, null=True, blank=True, db_column='destination')
    origin_snap = models.JSONField(null=True, blank=True)
    destination_snap = models.JSONField(null=True, blank=True)  # <— ditambahkan

    # --- Pihak terkait ---
    shipper = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='as_shipper_shipments', db_column='shipper_id'
    )
    consignee = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='as_consignee_shipments', db_column='consignee_id'
    )
    notify_party = models.ForeignKey(   # opsional
        Partner, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='as_notify_shipments', db_column='notify_party_id'
    )
    carrier = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='as_carrier_shipments', db_column='carrier_id'
    )
    agency = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='as_agency_shipments', db_column='agency_id'
    )

    # Snapshot pihak (opsional, sangat berguna untuk dokumen historis)
    shipper_snap = models.JSONField(null=True, blank=True)
    consignee_snap = models.JSONField(null=True, blank=True)
    carrier_snap = models.JSONField(null=True, blank=True)
    agency_snap = models.JSONField(null=True, blank=True)

    # --- Ringkasan kargo ---
    cargo_description = models.TextField(null=True, blank=True)
    weight = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)  # tonase total
    volume = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)  # CBM total
    qty = models.IntegerField(null=True, blank=True)                                      # total packages/pieces
    package_type = models.CharField(max_length=50, blank=True)                            # CTN, BAG, PALLET, dll.

    # --- Jadwal header (overall) ---
    etd = models.DateField(null=True, blank=True)   # planned ETD overall (boleh kosong jika pakai per leg)
    eta = models.DateField(null=True, blank=True)   # planned ETA overall
    atd = models.DateTimeField(null=True, blank=True)
    ata = models.DateTimeField(null=True, blank=True)

    # --- Transport ringkas di header (opsional; detail per leg ada di ShipmentRoute) ---
    mode = models.CharField(max_length=10, blank=True)           # SEA / LAND / AIR / RAIL (opsional)
    service_level = models.CharField(max_length=30, blank=True)  # FCL/LCL/FTL/LTL/Express, dll.
    inco_term = models.CharField(max_length=10, blank=True)      # FOB/CIF/DDP, dll.

    # Untuk ocean/air single-leg, kadang berguna:
    vessel_name = models.CharField(max_length=100, blank=True)
    voyage_no = models.CharField(max_length=50, blank=True)
    flight_no = models.CharField(max_length=50, blank=True)

    # --- Status & flag ---
    is_multimodal = models.BooleanField(default=False, db_column='is_multimoda')  # (kolom lama dipertahankan)

    # --- Financial ringkas (opsional; detail ada di modul costing/invoice) ---
    currency = models.CharField(max_length=10, blank=True, default='IDR')
    total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)  # bisa dipakai untuk summary costing

    # --- Audit ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shipments'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['number']),
            models.Index(fields=['status']),
            models.Index(fields=['booking_number']),
            models.Index(fields=['bill_of_lading_no']),
            models.Index(fields=['airwaybill_no']),
            models.Index(fields=['origin']),
            models.Index(fields=['destination']),
        ]
        permissions = [
            ("can_confirm_shipment", "Can confirm shipment"),
            ("can_book_shipment", "Can book shipment"),
        ]
        constraints = [
            # contoh constraint sederhana: origin != destination
            CheckConstraint(name='ck_shipment_origin_not_eq_dest', check=~Q(origin=F('destination'))),
        ]


    def can_confirm(self):
        return all([
            self.origin_id, self.destination_id,
            self.shipper_id, self.consignee_id,   # sesuaikan kebijakanmu
            self.routes.exists(),                 # minimal 1 route
        ])

    def can_book(self):
        # CONFIRMED dulu, minimal ada carrier & booking_number (boleh diisi di step booking)
        return self.status == 'CONFIRMED' and self.carrier_id and bool(self.booking_number)


    def __str__(self):
        return self.number or f"Shipment #{self.pk or 'new'}"

    def save(self, *args, **kwargs):
        # Snapshot helper mini
        def snap_loc(loc):
            if not loc: return None
            return {
                "id": loc.id,
                "code": getattr(loc, "code", None),
                "name": loc.name,
                "kind": getattr(loc, "kind", None),
                "address": getattr(loc, "address", None),
                "lat": getattr(loc, "lat", None),
                "lon": getattr(loc, "lon", None),
            }
        def snap_partner(p):
            if not p: return None
            return {
                "id": p.id,
                "code": getattr(p, "code", None),
                "name": getattr(p, "name", None),
                "tax_id": getattr(p, "tax_id", None),
                "address": getattr(p, "address", None),
                "phone": getattr(p, "phone", None),
            }

        # Isi text/snap lokasi bila kosong
        if self.origin and not self.origin_text:
            self.origin_text = self.origin.name
        if self.destination and not self.destination_text:
            self.destination_text = self.destination.name
        if self.origin and not self.origin_snap:
            self.origin_snap = snap_loc(self.origin)
        if self.destination and not self.destination_snap:
            self.destination_snap = snap_loc(self.destination)

        # Snapshot pihak (one-time fill)
        if self.shipper and not self.shipper_snap:
            self.shipper_snap = snap_partner(self.shipper)
        if self.consignee and not self.consignee_snap:
            self.consignee_snap = snap_partner(self.consignee)
        if self.carrier and not self.carrier_snap:
            self.carrier_snap = snap_partner(self.carrier)
        if self.agency and not self.agency_snap:
            self.agency_snap = snap_partner(self.agency)

        super().save(*args, **kwargs)

    @property
    def shipper_name(self):
        return self.shipper.name if self.shipper_id else "-"

    @property
    def consignee_name(self):
        return self.consignee.name if self.consignee_id else "-"

    @property
    def carrier_name(self):
        return self.carrier.name if self.carrier_id else "-"

    @property
    def agency_name(self):
        return self.agency.name if self.agency_id else "-"

    # --- Locations ---
    @property
    def origin_name(self):
        return self.origin.name if self.origin_id else (self.origin_text or "-")

    @property
    def destination_name(self):
        return self.destination.name if self.destination_id else (self.destination_text or "-")

    # --- Status / badge helper ---
    @property
    def status_badge_class(self):
        color_map = {
            "DRAFT": "secondary",
            "CONFIRMED": "info",
            "BOOKED": "primary",
            "IN_TRANSIT": "warning",
            "ARRIVED": "success",
            "CLOSED": "dark",
            "CANCELLED": "danger",
        }
        return color_map.get(self.status, "secondary")

    @property
    def status_label(self):
        return self.get_status_display() if hasattr(self, "get_status_display") else self.status.title()


class TransportationType(models.Model):
    MODE_CHOICES = [
        ('SEA', 'Sea'),
        ('LAND', 'Land'),
        ('AIR', 'Air'),
        ('RAIL', 'Rail'),
    ]
    
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)      # ex: FCL20, FCL40, BARGE300, TRUCK10R
    name = models.CharField(max_length=100)                  # ex: FCL 20', Barge 300 ft, Truck 10 Roda
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, null=True, blank=True, db_index=True)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self): return f"{self.name} ({self.mode})"


class TransportationAsset(models.Model):
    """Opsional: unit spesifik (truk/kapal/kontainer/flight)."""
    type = models.ForeignKey(TransportationType, on_delete=models.PROTECT, related_name='assets')
    carrier = models.ForeignKey(Partner, null=True, blank=True, on_delete=models.SET_NULL)
    identifier = models.CharField(max_length=100, db_index=True)  # no. polisi / vessel name / container / flight no
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self): return self.identifier


class ShipmentRoute(models.Model):
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('IN_TRANSIT', 'In Transit'),
        ('ARRIVED', 'Arrived'),
        ('DELAYED', 'Delayed'),
        ('CANCELLED', 'Cancelled'),
    ]

    shipment = models.ForeignKey('shipments.Shipment', on_delete=models.CASCADE, related_name='routes')
    driver_info = models.CharField(max_length=150, blank=True)  # contoh: "Budi – B 9123 KQ"

    # Lokasi (FK ketat sesuai pilihan A) + snapshot untuk stabilitas tampilan
    origin = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='route_origins', db_column='origin_id')
    destination = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='route_destinations', db_column='destination_id')
    origin_text = models.CharField(max_length=255, blank=True)
    destination_text = models.CharField(max_length=255, blank=True)
    origin_snap = models.JSONField(null=True, blank=True)
    destination_snap = models.JSONField(null=True, blank=True)

    # Transportasi (tipe wajib? bisa nullable dulu), plus snapshot text
    transportation_type = models.ForeignKey(TransportationType, on_delete=models.PROTECT, null=True, blank=True)
    transportation_type_text = models.CharField(max_length=100, blank=True)
    transportation_type_snap = models.JSONField(null=True, blank=True)

    # Unit/alat spesifik (opsional)
    transportation_asset = models.ForeignKey(TransportationAsset, on_delete=models.SET_NULL, null=True, blank=True)
    transportation_asset_text = models.CharField(max_length=100, blank=True)   # vessel/flight/plat/container
    transportation_asset_snap = models.JSONField(null=True, blank=True)

    carrier = models.ForeignKey(Partner, null=True, blank=True, on_delete=models.SET_NULL, related_name='routes_as_carrier')

    # Jadwal & aktual per leg
    planned_departure = models.DateTimeField(null=True, blank=True, db_index=True)  # ETD leg
    planned_arrival   = models.DateTimeField(null=True, blank=True, db_index=True)  # ETA leg
    actual_departure  = models.DateTimeField(null=True, blank=True)                  # ATD leg
    actual_arrival    = models.DateTimeField(null=True, blank=True)                  # ATA leg

    # Info rute
    order = models.PositiveIntegerField(default=0, help_text="Urutan rute dalam shipment")
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='PLANNED', db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shipment_routes'
        ordering = ["order", "id"]
        constraints = [
            # Origin/destination wajib terisi (FK), plus urutan unik per shipment
            models.UniqueConstraint(fields=['shipment', 'order'], name='uq_shipment_route_order'),
            # (opsional) cegah origin == destination
            CheckConstraint(
                name='ck_route_origin_not_eq_dest',
                check=~Q(origin=models.F('destination'))
            ),
        ]
        indexes = [
            models.Index(fields=['shipment', 'order']),
            models.Index(fields=['status']),
            models.Index(fields=['planned_departure']),
            models.Index(fields=['planned_arrival']),
        ]

    def __str__(self):
        return f"{self.shipment.number if self.shipment_id else 'Shipment?'} • {self.order}: {self.origin_text or self.origin_id} → {self.destination_text or self.destination_id}"

    def save(self, *args, **kwargs):
        # Snapshot helper
        def snap_loc(loc):
            if not loc: return None
            return {
                "id": loc.id,
                "code": getattr(loc, "code", None),
                "name": getattr(loc, "name", None),
                "kind": getattr(loc, "kind", None),
                "address": getattr(loc, "address", None),
                "lat": getattr(loc, "lat", None),
                "lon": getattr(loc, "lon", None),
            }

        if self.origin and not self.origin_text:
            self.origin_text = self.origin.name
        if self.destination and not self.destination_text:
            self.destination_text = self.destination.name
        if self.origin and not self.origin_snap:
            self.origin_snap = snap_loc(self.origin)
        if self.destination and not self.destination_snap:
            self.destination_snap = snap_loc(self.destination)

        if self.transportation_type and not self.transportation_type_text:
            self.transportation_type_text = self.transportation_type.name
        if self.transportation_type and not self.transportation_type_snap:
            self.transportation_type_snap = {
                "id": self.transportation_type_id,
                "code": self.transportation_type.code,
                "name": self.transportation_type.name,
                "mode": self.transportation_type.mode,
            }

        if self.transportation_asset and not self.transportation_asset_text:
            self.transportation_asset_text = self.transportation_asset.identifier
        if self.transportation_asset and not self.transportation_asset_snap:
            self.transportation_asset_snap = {
                "id": self.transportation_asset_id,
                "identifier": self.transportation_asset.identifier,
                "carrier_id": getattr(self.transportation_asset.carrier, "id", None),
                "carrier_name": getattr(self.transportation_asset.carrier, "name", None),
            }

        super().save(*args, **kwargs)

    @property
    def transportation_type_name(self):
        if self.transportation_type_id:
            return self.transportation_type.name
        return self.transportation_type_text or "-"

    @property
    def transportation_asset_identifier(self):
        if self.transportation_asset_id:
            return self.transportation_asset.identifier
        return self.transportation_asset_text or "-"

    @property
    def route_label(self):
        return f"{self.origin_text or '-'} → {self.destination_text or '-'}"


class ShipmentDocument(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=50)
    file_path = models.CharField(max_length=255, db_column='file_path')
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'shipment_documents'
        ordering = ['id']

   
# shipments/models.py
class ShipmentAttachment(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="shipments/%Y/%m/")
    label = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        import os
        return os.path.basename(self.file.name)

    class Meta:
        permissions = [
        ]
        pass

   