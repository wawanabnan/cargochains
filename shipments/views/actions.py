# shipments/views/actions.py
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST, require_http_methods

from django.shortcuts import get_object_or_404, redirect,render
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from shipments.models.shipments import Shipment,ShipmentAttachment
from shipments.services.transitions import confirm_shipment, book_shipment
from shipments.forms.shipment_parties import ShipmentPartiesForm


@login_required
@permission_required("shipments.can_confirm_shipment", raise_exception=True)
@require_POST
@transaction.atomic
def shipment_confirm(request, pk):
    shp = get_object_or_404(Shipment, pk=pk)
    try:
        confirm_shipment(shp, user=request.user)
        messages.success(request, f"Shipment {shp.number} telah di-CONFIRM.")
    except ValidationError as e:
        messages.error(request, e.messages[0])
    return redirect("shipments:shipment_details", pk=shp.pk)

@login_required
@permission_required("shipments.can_book_shipment", raise_exception=True)
@require_POST
@transaction.atomic
def shipment_book(request, pk):
    shp = get_object_or_404(Shipment, pk=pk)
    booking_no = (request.POST.get("booking_number") or "").strip()
    try:
        book_shipment(shp, user=request.user, booking_number=booking_no)
        messages.success(request, f"Shipment {shp.number} telah BOOKED dengan booking #{shp.booking_number}.")
    except ValidationError as e:
        messages.error(request, e.messages[0])
    return redirect("shipments:shipment_details", pk=shp.pk)
@login_required
@permission_required("shipments.add_shipmentattachment", raise_exception=True)
@require_POST
def shipment_attach(request, pk):
    shp = get_object_or_404(Shipment, pk=pk)
    f = request.FILES.get("file")
    if not f:
        messages.error(request, "File wajib dipilih.")
        return redirect("shipments:shipment_details", pk=shp.pk)
    att = ShipmentAttachment.objects.create(
        shipment=shp,
        file=f,
        label=request.POST.get("label", "").strip(),
        category=request.POST.get("category", "").strip(),
    )
    messages.success(request, f"Dokumen '{att.filename}' diunggah.")
    return redirect("shipments:shipment_details", pk=shp.pk)


@login_required
@permission_required("shipments.delete_shipmentattachment", raise_exception=True)
@require_POST
def shipment_detach(request, pk, att_pk):
    shp = get_object_or_404(Shipment, pk=pk)
    att = get_object_or_404(ShipmentAttachment, pk=att_pk, shipment=shp)
    name = att.filename
    att.delete()
    messages.success(request, f"Dokumen '{name}' dihapus.")
    return redirect("shipments:shipment_details", pk=shp.pk)



@login_required
@require_http_methods(["GET", "POST"])
def shipment_update_parties(request, pk):
    shp = get_object_or_404(Shipment, pk=pk)
    form = ShipmentPartiesForm(request.POST or None, instance=shp, sales_order=shp.sales_order)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            # (opsional) update snapshot shipper/consignee tiap simpan
            shp.refresh_from_db()
            def snap_partner(p):
                if not p: return None
                return {
                    "id": p.id, "code": getattr(p, "code", None), "name": getattr(p, "name", None),
                    "address": getattr(p, "address", None), "phone": getattr(p, "phone", None),
                    "email": getattr(p, "email", None),
                }
            if shp.shipper and not shp.shipper_snap:
                shp.shipper_snap = snap_partner(shp.shipper)
            if shp.consignee and not shp.consignee_snap:
                shp.consignee_snap = snap_partner(shp.consignee)
            shp.save(update_fields=["shipper_snap", "consignee_snap"])
            messages.success(request, "Parties & cargo updated.")
            return redirect("shipments:shipment_details", pk=shp.pk)
        messages.error(request, "Periksa kembali input Anda.")
    return render(request, "shipments/shipment_update_parties.html", {"form": form, "shipment": shp})


@login_required
@require_http_methods(["GET", "POST"])
def shipment_update_parties(request, pk):
    shp = get_object_or_404(Shipment, pk=pk)
    form = ShipmentPartiesForm(request.POST or None, instance=shp, sales_order=shp.sales_order)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            # (opsional) update snapshot shipper/consignee tiap simpan
            shp.refresh_from_db()
            def snap_partner(p):
                if not p: return None
                return {
                    "id": p.id, "code": getattr(p, "code", None), "name": getattr(p, "name", None),
                    "address": getattr(p, "address", None), "phone": getattr(p, "phone", None),
                    "email": getattr(p, "email", None),
                }
            if shp.shipper and not shp.shipper_snap:
                shp.shipper_snap = snap_partner(shp.shipper)
            if shp.consignee and not shp.consignee_snap:
                shp.consignee_snap = snap_partner(shp.consignee)
            shp.save(update_fields=["shipper_snap", "consignee_snap"])
            messages.success(request, "Parties & cargo updated.")
            return redirect("shipments:shipment_details", pk=shp.pk)
        messages.error(request, "Periksa kembali input Anda.")
    return render(request, "shipments/update_parties.html", {"form": form, "shipment": shp})
