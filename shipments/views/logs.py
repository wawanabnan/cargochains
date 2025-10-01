from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST
from ..models import Shipment
from ..forms import ShipmentStatusLogForm
from ..services.status import add_status

@login_required
@require_POST
def add_status_log(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    form = ShipmentStatusLogForm(request.POST)
    if form.is_valid():
        add_status(
            shipment,
            request.user,
            status=form.cleaned_data["status"],
            event_time=form.cleaned_data.get("event_time"),
            note=form.cleaned_data.get("note"),
        )
    return redirect("shipments:view", pk=pk)
