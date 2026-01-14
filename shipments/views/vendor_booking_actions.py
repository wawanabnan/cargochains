from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from job.models.job_orders import JobOrder
from shipments.services.vendor_booking_services import generate_vendor_bookings_from_job


@login_required
@require_POST
def generate_vendor_booking(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)

    bookings = generate_vendor_bookings_from_job(job, user=request.user)

    if bookings:
        messages.success(request, f"✅ Generated {len(bookings)} Vendor Booking (DRAFT).")
    else:
        messages.info(request, "ℹ️ Tidak ada cost line vendor yang perlu digenerate (atau sudah pernah digenerate).")

    return redirect("job:job_order_details", pk=job.pk)
