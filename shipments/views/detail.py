
from django.views.generic import DetailView
from ..models import Shipment, TransportationType
from ..selectors.shipments import shipment_detail_qs

class ShipmentDetailView(DetailView):
    model = Shipment
    template_name = "shipments/view.html"
    context_object_name = "s"

    def get_queryset(self):
        return shipment_detail_qs()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        s = ctx["s"]
        ctx["routes"] = s.routes.select_related("origin","destination","transportation_type")
        ctx["docs"] = s.documents.all()
        ctx["logs"] = s.status_logs.select_related("user").order_by("-event_time","-id")
        ctx["transport_qs"] = TransportationType.objects.all().order_by("name")
        return ctx
