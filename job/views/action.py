from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from core.utils.system_message import SystemMessage
from job.models.job_orders import JobOrder
from django.core.exceptions import ValidationError



@login_required
@require_POST
def job_confirm(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    try:
        job.confirm(request.user)  # Draft -> On Going
        job.save()
        messages.success(request, "Job confirmed: Draft → On Going")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)


@login_required
@require_POST
def job_hold(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    reason = (request.POST.get("reason") or "").strip()
    try:
        job.hold(request.user, reason)
        job.save()
        messages.warning(request, "Job moved to On Hold")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)


@login_required
@require_POST
def job_resume(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    try:
        job.resume(request.user)
        job.save()
        messages.success(request, "Job resumed: On Hold → On Going")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)


@login_required
@require_POST
def job_complete2(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    try:
        job.complete(request.user)  # complete() sudah save + posting
        messages.success(request, "Job completed")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)


@login_required
@require_POST
def job_cancel(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)
    reason = (request.POST.get("reason") or "").strip()
    try:
        job.cancel(request.user, reason)
        job.save()
        messages.warning(request, "Job cancelled")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("job:job_order_detail", pk=pk)



@login_required
def job_complete(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)

    try:
        job.complete(request.user)
        SystemMessage.success(
            request,
            f"Job <strong>{job.number}</strong> berhasil di-Complete.",
            modal=True,
            context="job-complete",
        )
    except ValidationError as e:
        SystemMessage.error(
            request,
            f"Gagal Complete Job <strong>{job.number}</strong>: {e}",
            modal=True,
            context="job-complete",
        )

    return redirect(request.META.get("HTTP_REFERER", "/"))
