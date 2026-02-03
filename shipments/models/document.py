# shipments/models/document.py
from django.conf import settings
from django.db import models

class ShipmentDocument(models.Model):

    DOC_TYPES = (
        ("POD", "Proof of Delivery"),
    )

    shipment = models.ForeignKey("shipments.Shipment", on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=24, choices=DOC_TYPES)    
    file = models.FileField(upload_to="shipment_docs/%Y/%m/",blank=True,null=True)
    is_public = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "shipments_documents"
        managed = False
        indexes = [
            models.Index(fields=["shipment", "doc_type"]),
            models.Index(fields=["shipment", "is_public"]),
        ]