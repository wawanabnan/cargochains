from django.db import transaction
from job.models.job_costs import JobCostType
from shipments.models.vendor_bookings import VendorBookingLine
from shipments.services.vendor_booking_desc import build_vendor_booking_description

@transaction.atomic
def apply_vendor_booking_line(
    line: VendorBookingLine,
    *,
    cost_type_id: int,
    details: dict,
    qty=None,
    uom="",
    description_manual: str | None = None,
):
    ct = JobCostType.objects.get(pk=cost_type_id)

    line.cost_type = ct
    line.service_type = ct.default_service_type or (line.service_type or "")
    line.details = details or {}

    if qty is not None:
        line.qty = qty
    if uom is not None:
        line.uom = uom or ""

    if description_manual is not None and str(description_manual).strip():
        line.description = str(description_manual).strip()
        line.description_is_manual = True
    else:
        if not line.description_is_manual:
            line.description = build_vendor_booking_description(
                line.service_type,
                line.cost_type.name if line.cost_type_id else "",
                line.details or {},
            )

    line.save()
    return line
