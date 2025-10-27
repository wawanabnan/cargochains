# shipments/views/lists.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from shipments.models import Shipment

class ShipmentListView(LoginRequiredMixin, ListView):
    model = Shipment
    template_name = "shipments/shipment_list.html"
    context_object_name = "shipments"
    paginate_by = 20  # optional

    def get_queryset(self):
        qs = super().get_queryset().order_by("-created_at")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs
