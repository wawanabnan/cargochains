from collections import defaultdict
from django.db import transaction
from django.db.models import Max

from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine

def _pick_service_type_from_cost_type(cost_type):
    """
    Ambil default_service_type dari CostType master.
    Fallback string kosong jika belum tersedia.
    """
    if not cost_type:
        return ""
    return getattr(cost_type, "default_service_type", "") or ""

@transaction.atomic
def generate_vendor_bookings_from_job(job_order, user=None):
    """
    Create DRAFT VendorBooking per (vendor, currency, exchange_rate) dari JobCost lines.
    - Hanya ambil line yang punya vendor (vendor_id not null).
    - Idempotent: kalau job cost sudah punya booking line, skip.
    - Booking tetap DRAFT.
    Return: list[VendorBooking] yang dibuat/diupdate (unik).
    """

    # Sesuaikan queryset sesuai nama related_name di project om
    # Misal: job_order.job_costs.all() atau job_order.costs.all()
    qs = job_order.job_costs.filter(is_active=True)  # <- sesuaikan

    # ambil hanya yang ada vendor
    qs = qs.filter(vendor_id__isnull=False)

    buckets = defaultdict(list)
    for jc in qs.select_related("vendor", "cost_type", "currency"):
        # idempotent: sudah pernah digenerate?
        if getattr(jc, "vendor_booking_line", None):
            continue

        key = (jc.vendor_id, jc.currency_id, str(jc.exchange_rate or ""))
        buckets[key].append(jc)

    created_or_touched = []

    for (vendor_id, currency_id, rate_str), lines in buckets.items():
        rate_val = lines[0].exchange_rate if lines else None

        # cari draft booking yang cocok (agar tidak spam booking header)
        booking = (
            VendorBooking.objects.filter(
                job_order=job_order,
                vendor_id=vendor_id,
                currency_id=currency_id,
                exchange_rate=rate_val,
                status=VendorBooking.ST_DRAFT,
            )
            .order_by("-id")
            .first()
        )

        if not booking:
            booking = VendorBooking.objects.create(
                job_order=job_order,
                vendor_id=vendor_id,
                currency_id=currency_id,
                exchange_rate=rate_val,
                status=VendorBooking.ST_DRAFT,
                created_by=user if user and user.is_authenticated else None,
            )
            created_or_touched.append(booking)

        # line_no next
        max_no = booking.lines.aggregate(m=Max("line_no"))["m"] or 0
        next_no = max_no + 1

        for jc in lines:
            # buat booking line dari job cost
            service_type = _pick_service_type_from_cost_type(jc.cost_type)

            VendorBookingLine.objects.create(
                booking=booking,
                line_no=next_no,
                service_type=service_type,
                description=jc.description or (jc.cost_type.name if jc.cost_type_id else ""),
                qty=getattr(jc, "qty", None),
                uom=getattr(jc, "uom_id", "") or "",
                details={
                    "generated_from": "job_cost",
                    "job_cost_id": jc.id,
                    # nanti bisa ditambah payload operasional di modal
                },
                source_job_cost=jc,
            )
            next_no += 1

    return created_or_touched
