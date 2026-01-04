from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Sum

from job.models.job_orders import JobOrder  # pastikan path ini benar di project kamu
from accounting.models.journal import Journal, JournalLine  # pastikan path ini benar di project kamu

DEC0 = Decimal("0.00")


@dataclass
class ProfitRow:
    job: JobOrder
    revenue: Decimal
    cogs: Decimal
    gp: Decimal
    margin: Decimal | None


class ProfitabilityService:
    def __init__(self, *, revenue_field: str = "amount"):
        self.revenue_field = revenue_field

    def get_jobs(self, *, date_from=None, date_to=None, customer_id=None, status=None, job_id=None):
        qs = JobOrder.objects.all().select_related("customer")

        if job_id:
            qs = qs.filter(id=job_id)

        if date_from:
            qs = qs.filter(job_date__gte=date_from)
        if date_to:
            qs = qs.filter(job_date__lte=date_to)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if status:
            qs = qs.filter(status=status)

        return qs.order_by("-job_date", "-id")

    def get_cogs_for_job(self, job: JobOrder) -> Decimal:
        jid = getattr(job, "complete_journal_id", None)
        if not jid:
            return DEC0

        # guard posted kalau field ada
        try:
            j = Journal.objects.only("id", "is_posted").get(id=jid)
            if hasattr(j, "is_posted") and not j.is_posted:
                return DEC0
        except Journal.DoesNotExist:
            return DEC0

        total = (
            JournalLine.objects
            .filter(journal_id=jid, debit__gt=0)
            .aggregate(s=Sum("debit"))["s"]
        )
        return total or DEC0

    def build_for_job(self, job: JobOrder) -> dict:
        revenue = getattr(job, self.revenue_field, None) or DEC0
        cogs = self.get_cogs_for_job(job)
        gp = revenue - cogs
        margin = (gp / revenue * Decimal("100.0")) if revenue else None
        return {"revenue": revenue, "cogs": cogs, "gp": gp, "margin": margin}

    def build(self, *, date_from=None, date_to=None, customer_id=None, status=None, job_id=None):
        rows: list[ProfitRow] = []
        totals = {"revenue": DEC0, "cogs": DEC0, "gp": DEC0}

        jobs = self.get_jobs(
            date_from=date_from,
            date_to=date_to,
            customer_id=customer_id,
            status=status,
            job_id=job_id,
        )

        for job in jobs:
            revenue = getattr(job, self.revenue_field, None) or DEC0
            cogs = self.get_cogs_for_job(job)
            gp = revenue - cogs
            margin = (gp / revenue * Decimal("100.0")) if revenue else None

            rows.append(ProfitRow(job=job, revenue=revenue, cogs=cogs, gp=gp, margin=margin))

            totals["revenue"] += revenue
            totals["cogs"] += cogs
            totals["gp"] += gp

        totals["margin"] = (totals["gp"] / totals["revenue"] * Decimal("100.0")) if totals["revenue"] else None
        return rows, totals

    def get_cogs_lines_for_job(self, job: JobOrder):
        """
        Kembalikan list JournalLine untuk complete_journal job.
        Kalau tidak ada journal -> [].
        """
        jid = getattr(job, "complete_journal_id", None)
        if not jid:
            return []

        # kalau mau enforce posted:
        try:
            j = Journal.objects.only("id", "is_posted").get(id=jid)
            if hasattr(j, "is_posted") and not j.is_posted:
                return []
        except Journal.DoesNotExist:
            return []

        # NOTE: kalau JournalLine punya select_related account, bagus:
        return list(
            JournalLine.objects
            .filter(journal_id=jid)
            .select_related("account")
            .order_by("id")
        )

class COGSJournalReportService:
    """
    Report audit jurnal COGS (ledger view).
    Default: posted only kalau field is_posted tersedia.
    """

    def get_journals(self, *, date_from=None, date_to=None, posted_only=True, journal_id=None):
        qs = Journal.objects.all()

        # kalau journal_type ada, filter COGS
        if hasattr(Journal, "journal_type"):
            qs = qs.filter(journal_type="COGS")

        # posted only (kalau field ada)
        if posted_only and hasattr(Journal, "is_posted"):
            qs = qs.filter(is_posted=True)

        if journal_id:
            qs = qs.filter(id=journal_id)

        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # prefetch lines; kalau related_name kamu bukan "lines", nanti kita sesuaikan
        return qs.order_by("-date", "-id").prefetch_related("lines")
