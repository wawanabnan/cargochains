from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from shipments.models import Shipment
from shipments.services.public_token import make_public_token


@login_required
def shipment_public_link_page(request, shipment_id: int):
    shipment = get_object_or_404(Shipment, pk=shipment_id)

    result = None
    if request.method == "POST":
        ttl_days = int(request.POST.get("ttl_days", "30"))
        ttl_days = max(1, min(ttl_days, 365))  # clamp

        token = make_public_token(shipment.tracking_no, ttl_seconds=ttl_days * 24 * 3600)
        expires_at = timezone.now() + timedelta(days=ttl_days)

        base = request.build_absolute_uri("/")[:-1]
        url =  f"/track/{shipment.tracking_no}/?t={token}"

        result = {
            "tracking_no": shipment.tracking_no,
            "ttl_days": ttl_days,
            "expires_at": expires_at,
            "url": url,
        }

    return render(
        request,
        "shipments/internal/public_link.html",
        {
            "shipment": shipment,
            "result": result,
            "ttl_default": 30,
        },
    )
