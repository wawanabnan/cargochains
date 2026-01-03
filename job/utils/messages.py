# job/utils/messages.py
from django.contrib import messages

class JobMessages:
    @staticmethod
    def complete_success(request, job):
        messages.success(
            request,
            f"Job <strong>{job.number}</strong> berhasil di-Complete.",
            extra_tags="modal job-complete"
        )

    @staticmethod
    def confirm_success(request, job):
        messages.success(
            request,
            f"Job <strong>{job.number}</strong> berhasil dikonfirmasi.",
            extra_tags="modal job-confirm"
        )

    @staticmethod
    def action_failed(request, action_label, error):
        messages.error(
            request,
            f"Gagal {action_label}: {error}",
            extra_tags="modal job-error"
        )
