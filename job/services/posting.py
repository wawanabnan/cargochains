# job/services/posting.py

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from accounting.models import JournalEntry, JournalLine
from core.services.settings import get_core_settings


def ensure_job_costing_posted(job):
    """
    Auto post COGS for job costing.
    Dipanggil SETIAP job COMPLETE.
    Idempotent (tidak bisa dobel posting).
    """

    settings = get_core_settings()
    if not settings.auto_post_job_costing:
        return

    # anti dobel posting (by source_ref)
    if JournalEntry.objects.filter(
        source_type="JOB",
        source_ref=job.number,
    ).exists():
        return

    costs = job.job_costs.filter(actual_amount__gt=0, is_active=True)
    if not costs.exists():
        return

    cogs_map = {}  # account_id -> amount

    for cost in costs:
        ct = cost.cost_type
        if not ct.cogs_account:
            raise ValidationError(
                f"Cost Type '{ct.name}' belum punya mapping COGS account"
            )

        acc_id = ct.cogs_account_id
        cogs_map.setdefault(acc_id, Decimal("0"))
        cogs_map[acc_id] += cost.actual_amount

    total_amount = sum(cogs_map.values())
    if total_amount <= 0:
        return

    accrued = settings.default_accrued_account
    if not accrued:
        raise ValidationError("Default accrued account belum diset di Core Settings")

    with transaction.atomic():
        journal = JournalEntry.objects.create(
            journal_date=job.completed_at.date(),
            description=f"COGS Job {job.number}",
            source_type="JOB",
            source_ref=job.number,
            currency=job.currency,
        )

        for acc_id, amount in cogs_map.items():
            JournalLine.objects.create(
                journal=journal,
                account_id=acc_id,
                debit=amount,
                credit=0,
            )

        JournalLine.objects.create(
            journal=journal,
            account=accrued,
            debit=0,
            credit=total_amount,
        )
