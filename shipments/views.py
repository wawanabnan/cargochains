
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Shipment, TransportationType
from .forms import ShipmentForm, RouteFormSet, DocumentFormSet, ShipmentStatusLogForm

@login_required
def shipment_list(request):
    qs = Shipment.objects.select_related("origin","destination").order_by("-id")[:200]
    return render(request, "shipments/shipment_list.html", {"shipments": qs})

@login_required
@transaction.atomic
def shipment_create(request):
    shipment = Shipment()
    if request.method == "POST":
        form = ShipmentForm(request.POST, instance=shipment)
        if form.is_valid():
            shipment = form.save()
            messages.success(request, "Draft shipment created.")
            return redirect("shipments:edit", pk=shipment.pk)
    else:
        form = ShipmentForm(instance=shipment)

    route_fs = RouteFormSet(instance=shipment, prefix="routes")
    doc_fs = DocumentFormSet(instance=shipment, prefix="docs")
    status_form = ShipmentStatusLogForm()

    transport_qs = TransportationType.objects.all().order_by("name")
    return render(request, "shipments/shipment_form.html", {
        "form": form,
        "route_formset": route_fs,
        "doc_formset": doc_fs,
        "status_form": status_form,
        "status_logs": [],
        "transport_qs": transport_qs,
    })

@login_required
@transaction.atomic
def shipment_edit(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    if request.method == "POST":
        form = ShipmentForm(request.POST, instance=shipment)
        route_fs = RouteFormSet(request.POST, instance=shipment, prefix="routes")
        doc_fs = DocumentFormSet(request.POST, instance=shipment, prefix="docs")
        if form.is_valid() and route_fs.is_valid() and doc_fs.is_valid():
            form.save()
            route_fs.save()
            doc_fs.save()
            messages.success(request, "Shipment updated.")
            return redirect("shipments:edit", pk=shipment.pk)
    else:
        form = ShipmentForm(instance=shipment)
        route_fs = RouteFormSet(instance=shipment, prefix="routes")
        doc_fs = DocumentFormSet(instance=shipment, prefix="docs")

    status_form = ShipmentStatusLogForm()
    transport_qs = TransportationType.objects.all().order_by("name")

    return render(request, "shipments/shipment_form.html", {
        "form": form,
        "route_formset": route_fs,
        "doc_formset": doc_fs,
        "status_form": status_form,
        "status_logs": shipment.status_logs.select_related("user").order_by("-event_time","-id")[:100],
        "transport_qs": transport_qs,
    })

@login_required
@transaction.atomic
def add_status_log(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    if request.method == "POST":
        form = ShipmentStatusLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.shipment = shipment
            log.user = request.user
            log.save()
            shipment.status = log.status
            shipment.save(update_fields=["status","updated_at"])
            messages.success(request, "Status log added.")
        else:
            messages.error(request, "Failed to add status log.")
    return redirect("shipments:edit", pk=shipment.pk)
