# shipments/services/transitions.py
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from shipments.models.shipments import Shipment

@transaction.atomic
def confirm_shipment(shipment: Shipment, *, user):
    if shipment.status != 'DRAFT':
        raise ValidationError("Hanya DRAFT yang bisa di-confirm.")
    if not shipment.can_confirm():
        raise ValidationError("Data wajib belum lengkap (origin/destination, shipper/consignee, dan minimal 1 route).")
    shipment.status = 'CONFIRMED'
    shipment.confirmed_at = timezone.now()
    shipment.confirmed_by = user
    shipment.save(update_fields=['status','confirmed_at','confirmed_by'])
    return shipment

@transaction.atomic
def book_shipment(shipment: Shipment, *, user, booking_number: str | None):
    if shipment.status != 'CONFIRMED':
        raise ValidationError("Hanya CONFIRMED yang bisa dibooking.")
    if not booking_number:
        raise ValidationError("Booking number wajib diisi.")
    if not shipment.carrier_id:
        raise ValidationError("Carrier wajib dipilih sebelum booking.")
    # set & simpan
    shipment.booking_number = booking_number
    shipment.status = 'BOOKED'
    shipment.booked_at = timezone.now()
    shipment.booked_by = user
    shipment.save(update_fields=['booking_number','status','booked_at','booked_by'])
    return shipment
