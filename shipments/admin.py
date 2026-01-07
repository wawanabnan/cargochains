# shipments/admin.py
from django.contrib import admin
from .models.vendor_bookings import VendorBooking, VendorBookingLine  # noqa
from .models.shipments import Shipment, ShipmentRoute, TransportationType, TransportationAsset
