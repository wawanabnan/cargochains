from decimal import Decimal
from django.db.models import Sum

def recalc_job_cost_vb(job_cost):
    """
    Hitung ulang alokasi Vendor Booking untuk satu JobCost.
    - vb_allocated_qty = sum(qty) dari VendorBookingLine terkait
    - vb_status: NONE / PARTIAL / FULL
    """
    from shipments.models.vendor_bookings import VendorBookingLine
    from job.models.costs import JobCost

    agg = VendorBookingLine.objects.filter(
        job_cost_id=job_cost.id,
        is_active=True,
        vendor_booking__isnull=False,
    ).aggregate(total=Sum("qty"))

    allocated = agg["total"] or Decimal("0")
    job_cost.vb_allocated_qty = allocated

    if allocated <= 0:
        job_cost.vb_status = JobCost.VB_NONE
    elif allocated >= (job_cost.qty or Decimal("0")):
        job_cost.vb_status = JobCost.VB_FULL
    else:
        job_cost.vb_status = JobCost.VB_PARTIAL

    job_cost.save(update_fields=["vb_allocated_qty", "vb_status"])
