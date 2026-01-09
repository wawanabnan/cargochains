from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Q
from shipments import models as m

def _booking_no(shp: m.shipments):
    so = getattr(shp, "sales_order", None)
    return getattr(so, "booking_number", None) or getattr(so, "number", None) or getattr(shp, "so_number", None)

def routes_schedule(request):
    """
    List jadwal ShipmentRoute dengan filter:
    - customer: id (GET: customer_id) atau nama (GET: customer_q)
    - booking: booking number/so number (GET: booking)
    - date range optional: from (etd>=), to (eta<=) (GET: date_from, date_to, format YYYY-MM-DD)
    """
    customer_id = request.GET.get("customer_id")
    customer_q  = request.GET.get("customer_q", "")
    booking_q   = request.GET.get("booking", "")
    date_from   = request.GET.get("date_from")
    date_to     = request.GET.get("date_to")

    qs = (
        m.ShipmentRoute.objects
        .select_related(
            "shipment",
            "shipment__shipper",
            "shipment__sales_order",
            "origin", "destination",
            "transportation_type", "transportation_asset",
        )
        .all()
    )

    if customer_id:
        qs = qs.filter(shipment__shipper_id=customer_id)
    elif customer_q:
        qs = qs.filter(
            Q(shipment__shipper__name__icontains=customer_q) |
            Q(shipment__shipper__code__icontains=customer_q)
        )

    if booking_q:
        qs = qs.filter(
            Q(shipment__sales_order__booking_number__icontains=booking_q) |
            Q(shipment__sales_order__number__icontains=booking_q) |
            Q(shipment__so_number__icontains=booking_q)
        )

    if date_from:
        qs = qs.filter(planned_departure__date__gte=date_from)
    if date_to:
        qs = qs.filter(planned_arrival__date__lte=date_to)

    qs = qs.order_by("planned_departure", "shipment_id", "order")

    paginator = Paginator(qs, 25)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    return render(request, "shipments/routes_schedule.html", {
        "page_obj": page_obj,
        "filters": {
            "customer_id": customer_id,
            "customer_q": customer_q,
            "booking": booking_q,
            "date_from": date_from,
            "date_to": date_to,
        }
    })


def routes_schedule_export(request):
    """Export CSV dengan filter yang sama."""
    request.GET._mutable = True  # hanya agar bisa reuse filter ringan (opsional di Django baru)
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="shipment_routes_schedule.csv"'

    import csv
    writer = csv.writer(resp)
    writer.writerow(["Booking No", "Shipment No", "Customer", "Leg", "Origin", "Destination",
                     "ETD", "ETA", "Type", "Asset", "Status"])

    # Reuse filter logic ringkas
    request.GET._mutable = False
    # panggil routes_schedule-like qs:
    from django.db.models import Q
    qs = (
        m.ShipmentRoute.objects
        .select_related("shipment","shipment__shipper","shipment__sales_order",
                        "origin","destination","transportation_type","transportation_asset")
        .all()
    )

    customer_id = request.GET.get("customer_id")
    customer_q  = request.GET.get("customer_q", "")
    booking_q   = request.GET.get("booking", "")
    date_from   = request.GET.get("date_from")
    date_to     = request.GET.get("date_to")

    if customer_id:
        qs = qs.filter(shipment__shipper_id=customer_id)
    elif customer_q:
        qs = qs.filter(Q(shipment__shipper__name__icontains=customer_q) | Q(shipment__shipper__code__icontains=customer_q))
    if booking_q:
        qs = qs.filter(
            Q(shipment__sales_order__booking_number__icontains=booking_q) |
            Q(shipment__sales_order__number__icontains=booking_q) |
            Q(shipment__so_number__icontains=booking_q)
        )
    if date_from:
        qs = qs.filter(planned_departure__date__gte=date_from)
    if date_to:
        qs = qs.filter(planned_arrival__date__lte=date_to)

    for r in qs.order_by("planned_departure","shipment_id","order"):
        shp = r.shipment
        writer.writerow([
            _booking_no(shp) or "-",
            getattr(shp, "number", "-"),
            getattr(getattr(shp, "shipper", None), "name", "-"),
            r.order or "-",
            r.origin_text or getattr(r.origin, "name", "-"),
            r.destination_text or getattr(r.destination, "name", "-"),
            r.planned_departure.isoformat() if r.planned_departure else "",
            r.planned_arrival.isoformat() if r.planned_arrival else "",
            r.transportation_type_text or getattr(getattr(r, "transportation_type", None), "name", "-"),
            r.transportation_asset_text or getattr(getattr(r, "transportation_asset", None), "identifier", "-"),
            r.status or "-",
        ])
    return resp
