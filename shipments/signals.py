# shipments/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models.shipments import Shipment
from .utils import next_shipment_number


@receiver(pre_save, sender=Shipment)
def set_shipment_number_and_snap(sender, instance: Shipment, **kwargs):
    # nomor otomatis jika belum ada
    if not instance.number:
        instance.number = next_shipment_number(timezone.localdate())

    # isi snapshot lokasi/partner bila kosong (jaga jika save() bawaan belum mengisi)
    def snap_loc(loc):
        if not loc:
            return None
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
        if not p:
            return None
        return {
            "id": p.id,
            "code": getattr(p, "code", None),
            "name": getattr(p, "name", None),
            "tax_id": getattr(p, "tax_id", None),
            "address": getattr(p, "address", None),
            "phone": getattr(p, "phone", None),
        }

    if instance.origin and not instance.origin_text:
        instance.origin_text = instance.origin.name
    if instance.destination and not instance.destination_text:
        instance.destination_text = instance.destination.name
    if instance.origin and not instance.origin_snap:
        instance.origin_snap = snap_loc(instance.origin)
    if instance.destination and not instance.destination_snap:
        instance.destination_snap = snap_loc(instance.destination)

    if getattr(instance, "shipper", None) and not getattr(instance, "shipper_snap", None):
        instance.shipper_snap = snap_partner(instance.shipper)
    if getattr(instance, "consignee", None) and not getattr(instance, "consignee_snap", None):
        instance.consignee_snap = snap_partner(instance.consignee)
    if getattr(instance, "carrier", None) and not getattr(instance, "carrier_snap", None):
        instance.carrier_snap = snap_partner(instance.carrier)
    if getattr(instance, "agency", None) and not getattr(instance, "agency_snap", None):
        instance.agency_snap = snap_partner(instance.agency)



from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

from shipments.models.vendor_bookings import VendorBookingLine
from shipments.services.vendor_booking_totals import recompute_vendor_booking_totals


@receiver(post_save, sender=VendorBookingLine)
def _vbline_saved(sender, instance, **kwargs):
    recompute_vendor_booking_totals(instance.vendor_booking)


@receiver(post_delete, sender=VendorBookingLine)
def _vbline_deleted(sender, instance, **kwargs):
    recompute_vendor_booking_totals(instance.vendor_booking)


@receiver(m2m_changed, sender=VendorBookingLine.taxes.through)
def _vbline_taxes_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        recompute_vendor_booking_totals(instance.vendor_booking)
