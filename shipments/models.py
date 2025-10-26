# shipments/models.py
from django.db import models
from django.conf import settings

STATUS_CHOICES = [
    ('DRAFT','DRAFT'), ('BOOKED','BOOKED'),
    ('IN_TRANSIT','IN_TRANSIT'), ('DELIVERED','DELIVERED'),
    ('CANCELLED','CANCELLED'),
]

class TransportationType(models.Model):
    name = models.CharField(max_length=50)
    transportation_mode = models.CharField(max_length=10)  # SEA/AIR/LAND
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'transportation_types'
        ordering = ['name']
    def __str__(self): return f"{self.name} ({self.transportation_mode})"

class Shipment(models.Model):
    number = models.CharField(max_length=30)  # set unique=True kalau mau
    so_number=models.CharField(max_length=30)  ;
    so_number=models.CharField(max_length=30)  ;
    origin = models.ForeignKey('geo.Location', on_delete=models.PROTECT,
                               related_name='shipment_origins', db_column='origin_id')
    destination = models.ForeignKey('geo.Location', on_delete=models.PROTECT,
                                    related_name='shipment_destinations', db_column='destination_id')
    cargo_description = models.TextField(null=True, blank=True)
    weight = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    volume = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    qty = models.IntegerField(null=True, blank=True)

    shipper = models.ForeignKey('partners.Partner', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='as_shipper_shipments', db_column='shipper_id')
    consignee = models.ForeignKey('partners.Partner', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='as_consignee_shipments', db_column='consignee_id')
    carrier = models.ForeignKey('partners.Partner', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='as_carrier_shipments', db_column='carrier_id')
    agency = models.ForeignKey('partners.Partner', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='as_agency_shipments', db_column='agency_id')

    etd = models.DateField(null=True, blank=True)
    eta = models.DateField(null=True, blank=True)
    atd = models.DateTimeField(null=True, blank=True)
    ata = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)
    is_multimodal = models.BooleanField(default=False, db_column='is_multimoda')

    origin_text = models.CharField(max_length=100, null=True, blank=True, db_column='origin')
    destination_text = models.CharField(max_length=100, null=True, blank=True, db_column='destination')

    bill_of_lading_no = models.CharField(max_length=50, null=True, blank=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shipments'
        ordering = ['-id']
        indexes = [models.Index(fields=['number']), models.Index(fields=['status'])]

    def __str__(self):
        return self.number or f"Shipment #{self.pk or 'new'}"

class ShipmentRoute(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='routes')
    origin = models.ForeignKey('geo.Location', on_delete=models.PROTECT,
                               related_name='route_origins', db_column='origin_id')
    destination = models.ForeignKey('geo.Location', on_delete=models.PROTECT,
                                    related_name='route_destinations', db_column='destination_id')
    transportation_type = models.ForeignKey('shipments.TransportationType', on_delete=models.RESTRICT,
                                            db_column='transportation_type_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'shipment_routes'
        ordering = ['id']

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

class ShipmentStatusLog(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    note = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    event_time = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             related_name='shipment_status_updates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'shipment_status_logs'
        indexes = [models.Index(fields=['shipment','event_time']), models.Index(fields=['status'])]

class ShipmentNumberSequence(models.Model):
    period = models.CharField(max_length=6, unique=True)  # YYYYMM
    last_no = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'shipment_number_sequences'
# models.py - same as previous shipment models
