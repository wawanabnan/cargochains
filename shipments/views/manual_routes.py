# shipments/views/routes_manual.py
from django.shortcuts import get_object_or_404, redirect, render
from django.forms import inlineformset_factory
from django.contrib import messages
from django.db import transaction

from shipments import models as m
from shipments.forms.shipment_parties import ShipmentPartiesForm
from shipments.forms.routes import ShipmentRouteForm



@transaction.atomic
def edit_routes(request, shipment_id):
    shipment = get_object_or_404(m.Shipment, pk=shipment_id)

    if request.method == "POST":
        formset = RouteFormSet(request.POST, instance=shipment, prefix="routes")
        if formset.is_valid():
            formset.save()
            # flag multimodal + mode dari leg pertama yang punya type
            shipment.is_multimodal = shipment.routes.count() > 1
            first = shipment.routes.filter(transportation_type__isnull=False).order_by("order").first()
            if first and hasattr(first.transportation_type, "mode"):
                shipment.mode = first.transportation_type.mode
            shipment.save(update_fields=["is_multimodal", "mode"])
            messages.success(request, "Shipment routes berhasil disimpan.")
            return redirect(shipment.get_absolute_url())
        else:
            messages.error(request, "Periksa kembali input rute.")
    else:
        formset = RouteFormSet(instance=shipment, prefix="routes")

    return render(request, "shipments/shipment_routes.html", {
        "shipment": shipment,
        "formset": formset,
    })
