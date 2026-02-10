# Compat layer: keep old import path working
from work_orders.models.vendor_bookings import VendorBooking, VendorBookingLine

__all__ = ["VendorBooking", "VendorBookingLine"]
