from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, OuterRef, Subquery, DecimalField, Value, F
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from job.models.job_orders import JobOrder
from job.models.job_costs import JobCost
from work_orders.models.vendor_bookings import VendorBooking, VendorBookingLine

# pakai helper yang sudah ada di file om (kalau class ini ditaruh di file yang sama, ga perlu import)
# from shipments.views.vendor_bookings import _get_cost_group_from_jobcost

def _to_decimal(val: str) -> Decimal:
    try:
        return Decimal(str(val or "").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


class VendorBookingCreateView(LoginRequiredMixin, TemplateView):
    """
    /vendor-bookings/create/
    - GET : render page + dropdown job order (eligible-only)
    - POST: create VB dari selected cost lines (logic sama seperti wizard lama)
    """
    template_name = "vendor_bookings/create.html"

    def _eligible_job_orders(self):
        """
        Job Order eligible-only:
        - punya minimal 1 JobCost vendor (requires_vendor, vendor not null, is_active)
        - remaining qty > 0, dihitung dari SUM(VendorBookingLine.qty)
        """
        used_sq = (
            VendorBookingLine.objects
            .filter(job_cost_id=OuterRef("pk"))
            .values("job_cost_id")
            .annotate(s=Sum("qty"))
            .values("s")[:1]
        )

        eligible_jobcosts = (
            JobCost.objects
            .filter(
                is_active=True,
                cost_type__requires_vendor=True,
                vendor__isnull=False,
                job_order__status__in=[JobOrder.ST_DRAFT, JobOrder.ST_IN_PROGRESS, JobOrder.ST_ON_HOLD],
            )
            .annotate(
                used_qty=Coalesce(Subquery(used_sq, output_field=DecimalField()), Value(0))
            )
            .annotate(
                remaining_qty=F("qty") - F("used_qty")
            )
            .filter(remaining_qty__gt=0)
        )

        eligible_job_ids = (
            eligible_jobcosts.values_list("job_order_id", flat=True).distinct()
        )

        return (
            JobOrder.objects
            .filter(id__in=eligible_job_ids)
            .order_by("-id")[:200]
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["job_orders"] = self._eligible_job_orders()
        return ctx

    def _used_map_for_job(self, job: JobOrder):
        job_cost_ids = list(
            JobCost.objects.filter(job_order=job).values_list("id", flat=True)
        )
        if not job_cost_ids:
            return {}

        sums = (
            VendorBookingLine.objects
            .filter(job_cost_id__in=job_cost_ids)
            .values("job_cost_id")
            .annotate(used=Sum("qty"))
        )
        return {row["job_cost_id"]: (row["used"] or Decimal("0")) for row in sums}

    def post(self, request, *args, **kwargs):
        job_id = (request.POST.get("job_order") or "").strip()
        if not job_id.isdigit():
            messages.error(request, "Job Order wajib dipilih.")
            return redirect("shipments:vendor_booking_create")

        job = get_object_or_404(JobOrder, pk=int(job_id))

        picked_ids = request.POST.getlist("pick")
        if not picked_ids:
            messages.error(request, "Pilih minimal 1 cost line.")
            return redirect("shipments:vendor_booking_create")

        selected = list(
            JobCost.objects
            .filter(
                job_order=job,
                id__in=picked_ids,
                is_active=True,
                cost_type__requires_vendor=True,
            )
            .exclude(vendor__isnull=True)
            .select_related("vendor", "cost_type")
        )
        if not selected:
            messages.error(request, "Cost line terpilih tidak valid.")
            return redirect("shipments:vendor_booking_create")

        used_map = self._used_map_for_job(job)

        locked_vendor_id = selected[0].vendor_id
        locked_group = _get_cost_group_from_jobcost(selected[0])

        errors = []
        lines_payload = []

        for jc in selected:
            # vendor harus sama
            if jc.vendor_id != locked_vendor_id:
                errors.append("Vendor tidak konsisten. Pilih cost line dengan vendor yang sama.")
                break

            # cost_group harus sama
            jc_group = _get_cost_group_from_jobcost(jc)
            if jc_group != locked_group:
                errors.append("Group tidak konsisten. Pilih cost line dengan cost_group yang sama.")
                break

            raw_qty = (request.POST.get(f"qty_{jc.id}", "") or "").strip()

            qty_total = jc.qty or Decimal("0")
            used = used_map.get(jc.id, Decimal("0"))
            remaining = qty_total - used

            alloc = remaining if raw_qty == "" else _to_decimal(raw_qty)

            if alloc <= 0:
                errors.append(f"Qty allocate harus > 0 untuk: {jc.cost_type.name}")
                continue

            if alloc > remaining:
                errors.append(f"Qty allocate melebihi remaining untuk: {jc.cost_type.name} (remaining {remaining})")
                continue

            lines_payload.append((jc, alloc))

        if errors:
            for e in errors[:3]:
                messages.error(request, e)
            if len(errors) > 3:
                messages.error(request, f"({len(errors)-3} error lain)")
            return redirect("shipments:vendor_booking_create")

        if not lines_payload:
            messages.error(request, "Tidak ada line valid untuk dibuat.")
            return redirect("shipments:vendor_booking_create")

        vb = VendorBooking(
            job_order=job,
            vendor_id=locked_vendor_id,
            status=VendorBooking.ST_DRAFT,
            discount_amount=Decimal("0"),
        )
        vb.save()

        def _jc_price(jc):
            val = getattr(jc, "actual_amount", None)
            if not val or Decimal(val or 0) == 0:
                val = getattr(jc, "est_amount", None)
            return Decimal(val or 0)

        vb_lines = []
        for (jc, alloc) in lines_payload:
            unit_price = _jc_price(jc)
            qty = Decimal(alloc or 0)
            amount = (qty * unit_price).quantize(Decimal("0.01"))

            desc = (getattr(jc, "description", "") or "") or (jc.cost_type.name if jc.cost_type_id else "")
            uom_id = jc.cost_type.uom_id if jc.cost_type_id else None

            vb_lines.append(VendorBookingLine(
                vendor_booking=vb,
                job_cost=jc,
                cost_type_id=jc.cost_type_id,
                cost_group=_get_cost_group_from_jobcost(jc),
                uom_id=uom_id,
                qty=qty,
                unit_price=unit_price,
                amount=amount,
                description=desc,
            ))

        VendorBookingLine.objects.bulk_create(vb_lines)

        update_url = reverse("work_orders:vendor_booking_update", args=[vb.id])
        return redirect(f"{update_url}?job_order={job.id}")


class VendorBookingCreateJobCostsPartialView(LoginRequiredMixin, View):
    """
    AJAX: /vendor-bookings/create/jobcosts/?job_order=123
    return HTML partial rows/table
    """
    template_name = "vendor_bookings/partials/_jobcost_rows.html"

    def _used_map_for_job(self, job: JobOrder):
        job_cost_ids = list(
            JobCost.objects.filter(job_order=job).values_list("id", flat=True)
        )
        if not job_cost_ids:
            return {}

        sums = (
            VendorBookingLine.objects
            .filter(job_cost_id__in=job_cost_ids)
            .values("job_cost_id")
            .annotate(used=Sum("qty"))
        )
        return {row["job_cost_id"]: (row["used"] or Decimal("0")) for row in sums}

    def get(self, request):
        job_id = (request.GET.get("job_order") or "").strip()
        job = get_object_or_404(JobOrder, pk=job_id)

        used_map = self._used_map_for_job(job)

        qs = (
            JobCost.objects
            .filter(
                job_order=job,
                is_active=True,
                cost_type__requires_vendor=True,
            )
            .exclude(vendor__isnull=True)
            .select_related("vendor", "cost_type")
            .order_by("vendor__name", "cost_type__cost_group", "cost_type__name", "id")
        )

        rows = []
        for jc in qs:
            qty = jc.qty or Decimal("0")
            used = used_map.get(jc.id, Decimal("0"))
            remaining = qty - used
            if remaining <= 0:
                continue

            unit_price = (jc.actual_amount if getattr(jc, "actual_amount", 0) else jc.est_amount) or Decimal("0")

            rows.append({
                "jc": jc,
                "vendor_name": (getattr(jc.vendor, "name", str(jc.vendor)) if jc.vendor_id else ""),
                "cost_type_name": (jc.cost_type.name if jc.cost_type_id else ""),
                "cost_group": _get_cost_group_from_jobcost(jc),
                "uom": getattr(jc, "uom", "") or "",
                "remaining": remaining,
                "unit_price": unit_price,
            })

        return render(request, self.template_name, {"job": job, "rows": rows})
