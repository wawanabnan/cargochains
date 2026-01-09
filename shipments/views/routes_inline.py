# shipments/views/routes_inline.py
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Max
from django.views.decorators.http import require_POST

from shipments.models.shipments import Shipment, ShipmentRoute
from shipments.forms.routes import ShipmentRouteForm

TEMPLATE_PARTIAL = "shipments/_routes_form.html"
TEMPLATE_WRAPPER = "shipments/routes_form_wrapper.html"
TEMPLATE_DELETE_CONFIRM = "shipments/_routes_delete_confirm.html"

def route_modal(request, shipment_id, route_id=None):
    shipment = get_object_or_404(Shipment, pk=shipment_id)
    instance = ShipmentRoute.objects.filter(pk=route_id, shipment=shipment).first()

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    force_wrapper = request.GET.get("debug") == "1"

    if request.method == "POST":
        form = ShipmentRouteForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.shipment = shipment
            obj.save()
            html = render(request, "shipments/_routes_table.html", {"shipment": shipment}).content.decode("utf-8")
            return JsonResponse({"ok": True, "html": html})
        tpl = TEMPLATE_PARTIAL if (is_ajax and not force_wrapper) else TEMPLATE_WRAPPER
        return render(request, tpl, {"form": form, "route": instance, "shipment": shipment}, status=400)

    # GET
    form = ShipmentRouteForm(instance=instance)
    next_order = (shipment.routes.aggregate(m=Max("order"))["m"] or 0) + 1
    ctx = {"form": form, "route": instance, "shipment": shipment, "next_order": next_order}
    tpl = TEMPLATE_PARTIAL if (is_ajax and not force_wrapper) else TEMPLATE_WRAPPER
    return render(request, tpl, ctx)


def route_delete_confirm(request, shipment_id, route_id):
    """GET modal konfirmasi delete."""
    shipment = get_object_or_404(Shipment, pk=shipment_id)
    route = get_object_or_404(ShipmentRoute, pk=route_id, shipment=shipment)
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    tpl = TEMPLATE_DELETE_CONFIRM if is_ajax else TEMPLATE_WRAPPER
    return render(request, tpl, {"shipment": shipment, "route": route})


@require_POST
def route_delete(request, shipment_id, route_id):
    """POST hapus route lalu kembalikan tabel terbaru (JSON)."""
    shipment = get_object_or_404(Shipment, pk=shipment_id)
    route = get_object_or_404(ShipmentRoute, pk=route_id, shipment=shipment)
    route.delete()
    html = render(request, "shipments/_routes_table.html", {"shipment": shipment}).content.decode("utf-8")
    return JsonResponse({"ok": True, "html": html})
