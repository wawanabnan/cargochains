from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.db import transaction
from shipments import models as m
from shipments.forms.routes import ShipmentRouteForm

def _render_routes_table(request, shipment: m.Shipment):
    return render(request, "shipments/_routes_table.html", {"shipment": shipment}).content.decode("utf-8")

def _next_order(shipment: m.Shipment) -> int:
    last = shipment.routes.order_by("-order").first()
    return (last.order + 1) if last and last.order else shipment.routes.count() + 1

@require_http_methods(["GET", "POST"])
@transaction.atomic
def route_modal(request, shipment_id: int, route_id: int | None = None):
    shipment = get_object_or_404(m.Shipment, pk=shipment_id)

    if route_id:
        route = get_object_or_404(m.ShipmentRoute, pk=route_id, shipment=shipment)
    else:
        route = m.ShipmentRoute(shipment=shipment, order=_next_order(shipment))

    if request.method == "GET":
        form = ShipmentRouteForm(instance=route, prefix="route")
        return render(request, "shipments/_routes_form_modal.html", {"shipment": shipment, "form": form, "route": route})

    # POST
    form = ShipmentRouteForm(request.POST, instance=route, prefix="route")
    if form.is_valid():
        saved = form.save(commit=False)
        saved.shipment = shipment
        if not saved.order:
            saved.order = _next_order(shipment)
        saved.save()
        # update flags di header
        shipment.is_multimodal = shipment.routes.count() > 1
        first = shipment.routes.filter(transportation_type__isnull=False).order_by("order").first()
        if first and hasattr(first.transportation_type, "mode"):
            shipment.mode = first.transportation_type.mode
        shipment.save(update_fields=["is_multimodal", "mode"])
        html = _render_routes_table(request, shipment)
        return JsonResponse({"ok": True, "html": html})
    else:
        return render(request, "shipments/_route_form_modal.html", {"shipment": shipment, "form": form, "route": route}, status=400)

@require_http_methods(["POST"])
@transaction.atomic
def route_delete(request, shipment_id: int, route_id: int):
    shipment = get_object_or_404(m.Shipment, pk=shipment_id)
    route = get_object_or_404(m.ShipmentRoute, pk=route_id, shipment=shipment)
    route.delete()
    # rapikan order 1..n
    for i, r in enumerate(shipment.routes.order_by("order"), start=1):
        if r.order != i:
            r.order = i
            r.save(update_fields=["order"])
    shipment.is_multimodal = shipment.routes.count() > 1
    first = shipment.routes.filter(transportation_type__isnull=False).order_by("order").first()
    if first and hasattr(first.transportation_type, "mode"):
        shipment.mode = first.transportation_type.mode
    shipment.save(update_fields=["is_multimodal", "mode"])
    html = _render_routes_table(request, shipment)
    return JsonResponse({"ok": True, "html": html})
