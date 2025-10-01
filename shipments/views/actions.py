from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from ..models import Shipment
from ..forms import ShipmentQuickActionForm
from ..services.status import add_status
from ..services.numbering import next_shipment_number

@login_required
@require_POST
def quick_action(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    form = ShipmentQuickActionForm(request.POST)
    if form.is_valid():
        action = form.cleaned_data["action"]
        add_status(shipment, request.user, status=action)
        messages.success(request, f"Shipment set to {action}.")
    return redirect("shipments:view", pk=pk)

@login_required
@require_POST
def assign_number(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    if not shipment.number:
        shipment.number = next_shipment_number()
        shipment.save(update_fields=["number", "updated_at"])
        messages.success(request, f"Assigned number {shipment.number}.")
    else:
        messages.info(request, f"Already numbered: {shipment.number}.")
    return redirect("shipments:view", pk=pk)
