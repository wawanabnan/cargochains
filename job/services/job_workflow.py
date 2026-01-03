from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from job.services.posting import ensure_job_costing_posted


def complete_job(job, user=None):
    # pastikan status benar
    if job.status != job.ST_IN_PROGRESS:
        raise ValidationError("Status job harus In Progress untuk bisa di-Complete.")

    costs = job.job_costs.filter(is_active=True)

    # ✅ Accrual basis: actual TIDAK wajib
    # Pilihan disiplin:
    # - tetap wajib ada cost? (tetap seperti sekarang)
    # - atau boleh complete tanpa cost (skip posting)
    if not costs.exists():
        raise ValidationError("Tidak bisa Complete: belum ada job cost.")

    # ✅ (Opsional) jika mau disiplin estimate, aktifkan:
    # if not costs.filter(est_amount__gt=0).exists():
    #     raise ValidationError("Tidak bisa Complete: Estimate Amount belum diisi.")

    with transaction.atomic():
        # set completed dulu (biar journal_date aman dipakai posting)
        job.status = job.ST_COMPLETED
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])

        # auto journal accrued COGS (pakai ESTIMATE)
        ensure_job_costing_posted(job)
