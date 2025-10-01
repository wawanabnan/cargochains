from django.views.generic import ListView
from ..selectors.shipments import shipment_list_qs
from ..models import STATUS_CHOICES

class ShipmentListView(ListView):
    template_name = "shipments/list.html"
    context_object_name = "shipments"

    def get_queryset(self):
        return shipment_list_qs(
            q=self.request.GET.get("q"),
            status=self.request.GET.get("status")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["status"] = self.request.GET.get("status", "")
        ctx["STATUSES"] = [key for key, _ in STATUS_CHOICES]   # ← kirim list status
        return ctx
