# shipments/views/details.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from shipments.models.shipments import Shipment

class ShipmentDetailView(LoginRequiredMixin, DetailView):
    model = Shipment
    template_name = "shipments/shipment_details.html"  # bikin templatenya di bawah
    context_object_name = "shipment"
