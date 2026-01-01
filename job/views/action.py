from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from job.models.job_orders import JobOrder


@login_required
def job_confirm(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    try:
        job.confirm(request.user)  # Draft -> On Going
        messages.success(request, "Job confirmed: Draft → On Going")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)


@login_required
def job_hold(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    reason = (request.POST.get("reason") or "").strip()
    try:
        job.hold(request.user, reason)
        messages.warning(request, "Job moved to On Hold")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)


@login_required
def job_resume(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    try:
        job.resume(request.user)
        messages.success(request, "Job resumed: On Hold → On Going")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)


@login_required
def job_complete(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    try:
        job.complete(request.user)
        messages.success(request, "Job completed")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)


@login_required
def job_cancel(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    reason = (request.POST.get("reason") or "").strip()
    try:
        job.cancel(request.user, reason)
        messages.warning(request, "Job cancelled")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)
