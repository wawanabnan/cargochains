from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from job.models.job_orders import JobOrder
from job.models.costs import JobCost
from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine
from shipments.services.vendor_booking_totals import recompute_vendor_booking_totals
from django.views.generic import ListView
from django.views.generic import ListView, CreateView, DetailView, UpdateView, View



def _to_decimal(val: str) -> Decimal:
    try:
        return Decimal(str(val or "").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _norm_group(s: str) -> str:
    return (s or "").strip().upper()


def _get_cost_group_from_jobcost(jc: JobCost) -> str:
    # sumber kebenaran: JobCostType.cost_group
    if getattr(jc, "cost_type_id", None) and getattr(jc, "cost_type", None):
        return _norm_group(getattr(jc.cost_type, "cost_group", "") or "")
    return ""


def _letter_type_from_mode(job: JobOrder) -> str:
    """
    RULE ringkasan:
    SEA -> SI
    AIR -> SLI
    INLAND/TRUCK -> SO
    lainnya -> WO
    """
    mode = (getattr(job, "mode", "") or "").upper().strip()
    if mode == "SEA":
        return "SI"
    if mode == "AIR":
        return "SLI"
    if mode in ("INLAND", "TRUCK", "TRUCKING"):
        return "SO"
    return "WO"


def _pick_unit_price(jc: JobCost) -> Decimal:
    """
    Harga default untuk VendorBookingLine (PO) diambil dari JobCost:
    prioritas: rate -> price -> 0
    """
    r = Decimal(getattr(jc, "rate", 0) or 0)
    if r > 0:
        return r
    p = Decimal(getattr(jc, "price", 0) or 0)
    if p > 0:
        return p
    return Decimal("0")


def _get_uom_from_jobcost(jc: JobCost) -> str:
    if getattr(jc, "cost_type", None):
        uom = getattr(jc.cost_type, "uom", "") or ""
        if uom.strip():
            return uom.strip()

    # fallback: JobCost.uom (kalau ada)
    return (getattr(jc, "uom", "") or "").strip()


class VendorBookingFromJobCostWizardOldView(LoginRequiredMixin, TemplateView):
    template_name = "vendor_bookings/from_wizard.html"

    # ---------- helpers ----------
    def _get_job(self):
        job_id = self.request.GET.get("job_order") or self.request.POST.get("job_order")
        if not job_id:
            return None
        return get_object_or_404(JobOrder, pk=job_id)

    def _used_map_for_job(self, job: JobOrder):
        """
        Map used qty per job_cost_id:
        used = SUM(VendorBookingLine.qty) group by job_cost_id
        """
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

    # ---------- GET ----------
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = self._get_job()
        ctx["job"] = job

        if not job:
            ctx["rows"] = []
            return ctx

        used_map = self._used_map_for_job(job)

        # Eligible lines:
        qs = (
            JobCost.objects
            .filter(job_order=job, cost_type__requires_vendor=True)
            .exclude(vendor__isnull=True)
            .select_related("vendor", "cost_type")
            # tampilan rapi: vendor -> group -> id
            .order_by("vendor__name", "cost_type__cost_group", "id")
        )

        rows = []
        for jc in qs:
            qty = jc.qty or Decimal("0")
            used = used_map.get(jc.id, Decimal("0"))
            remaining = qty - used

            if remaining > 0:
                cost_group = _get_cost_group_from_jobcost(jc)
                unit_price = _pick_unit_price(jc)
                rows.append({
                    "jc": jc,
                    "cost_type_name": (jc.cost_type.name if getattr(jc, "cost_type_id", None) else ""),
                    "qty": qty,
                    "used": used,
                    "remaining": remaining,
                    "vendor_id": jc.vendor_id,
                    "vendor_name": (getattr(jc.vendor, "name", str(jc.vendor)) if jc.vendor_id else ""),
                    "cost_group": cost_group,
                    "unit_price": unit_price,  # info display
                    "uom": getattr(jc, "uom", "") or "",
                })

        ctx["rows"] = rows
        return ctx

    # ---------- POST ----------
    def post(self, request, *args, **kwargs):
        job = self._get_job()
        if not job:
            messages.error(request, "Job Order tidak valid.")
            return redirect("job:job_order_list")  # sesuaikan kalau beda

        picked_ids = request.POST.getlist("pick")
        if not picked_ids:
            messages.error(request, "Pilih minimal 1 cost line.")
            return redirect(f"{reverse('shipments:vendor_booking_from_jobcost')}?job_order={job.id}")

        selected = list(
            JobCost.objects
            .filter(job_order=job, id__in=picked_ids, cost_type__requires_vendor=True)
            .exclude(vendor__isnull=True)
            .select_related("vendor", "cost_type")
        )
        if not selected:
            messages.error(request, "Cost line terpilih tidak valid.")
            return redirect(f"{reverse('shipments:vendor_booking_from_jobcost')}?job_order={job.id}")

        used_map = self._used_map_for_job(job)

        # server-side LOCK vendor + group (group dari cost_type)
        locked_vendor_id = selected[0].vendor_id
        locked_group = _get_cost_group_from_jobcost(selected[0])

        errors = []
        lines_payload = []

        for jc in selected:
            if jc.vendor_id != locked_vendor_id:
                errors.append("Vendor tidak konsisten. Pilih cost line dengan vendor yang sama.")
                break

            jc_group = _get_cost_group_from_jobcost(jc)
            if jc_group != locked_group:
                errors.append("Group tidak konsisten. Pilih cost line dengan cost_group yang sama.")
                break

            alloc = _to_decimal(request.POST.get(f"qty_{jc.id}", "0"))
            if alloc <= 0:
                errors.append(f"Qty allocate harus > 0 untuk line: {jc.cost_type.name if jc.cost_type_id else jc.description}")
                continue

            qty = jc.qty or Decimal("0")
            used = used_map.get(jc.id, Decimal("0"))
            remaining = qty - used

            if alloc > remaining:
                errors.append(
                    f"Qty allocate melebihi remaining untuk line: "
                    f"{jc.cost_type.name if jc.cost_type_id else jc.description} "
                    f"(remaining {remaining}, input {alloc})"
                )
                continue

            # pastikan cost_type_id ada (karena VBLine butuh cost_type_id NOT NULL)
            if not jc.cost_type_id:
                errors.append(f"Cost Type kosong pada JobCost #{jc.id}. Isi cost_type dulu.")
                continue

            lines_payload.append((jc, alloc))

        if errors:
            for e in errors[:3]:
                messages.error(request, e)
            if len(errors) > 3:
                messages.error(request, f"({len(errors) - 3} error lain)")
            return redirect(f"{reverse('shipments:vendor_booking_from_jobcost')}?job_order={job.id}")

        if not lines_payload:
            messages.error(request, "Tidak ada line valid untuk dibuat.")
            return redirect(f"{reverse('shipments:vendor_booking_from_jobcost')}?job_order={job.id}")

        # Create VendorBooking (DRAFT)
        vb = VendorBooking(
            job_order=job,
            vendor_id=locked_vendor_id,
            letter_type=_letter_type_from_mode(job),
            status="DRAFT",
            issued_date=timezone.localdate(),
            discount_amount=Decimal("0"),
            # currency & idr_rate sudah ada di header (di form / default)
            # wht_rate default 0 (field baru di model)
        )
        vb.save()

        # Create lines (bulk_create) — HARUS set unit_price + amount manual
        vb_lines = []
        for (jc, alloc) in lines_payload:
            unit_price = _pick_unit_price(jc)
            amount = (Decimal(alloc) * unit_price).quantize(Decimal("0.01"))

            vb_lines.append(
                VendorBookingLine(
                    vendor_booking=vb,
                    job_cost=jc,
                    cost_type_id=jc.cost_type_id,
                    qty=alloc,
                    uom=getattr(jc, "uom", "") or "",
                    unit_price=unit_price,
                    amount=amount,
                    cost_group=_get_cost_group_from_jobcost(jc),
                )
            )

        VendorBookingLine.objects.bulk_create(vb_lines)

        # Recompute header totals: wht_amount + total_amount (tax dari taxes line)
        recompute_vendor_booking_totals(vb)

        # redirect ke review/action (edit)
        edit_url = reverse("shipments:vendor_booking_edit", args=[vb.id])  # sesuaikan kalau name beda
        return redirect(f"{edit_url}?job_order={job.id}")



class VendorBookingFromJobCostWizardView(LoginRequiredMixin, TemplateView):
    template_name = "vendor_bookings/from_wizard.html"

    def _get_job(self):
        job_id = self.request.GET.get("job_order") or self.request.POST.get("job_order")
        if not job_id:
            return None
        return get_object_or_404(JobOrder, pk=job_id)

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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = self._get_job()
        ctx["job"] = job
        ctx["rows"] = []

        if not job:
            return ctx

        used_map = self._used_map_for_job(job)

        qs = (
            JobCost.objects
            .filter(job_order=job, cost_type__requires_vendor=True)
            .exclude(vendor__isnull=True)
            .select_related("vendor", "cost_type")
            .order_by(
                "vendor__name",
                "cost_type__cost_group",
                "cost_type__name",
                "id",
            )
        )

        rows = []
        for jc in qs:
            qty = jc.qty or Decimal("0")
            used = used_map.get(jc.id, Decimal("0"))
            remaining = qty - used

            if remaining <= 0:
                continue

            rows.append({
                "jc": jc,
                "cost_type_name": (jc.cost_type.name if jc.cost_type_id else ""),
                "cost_group": _get_cost_group_from_jobcost(jc),
                "vendor_name": (getattr(jc.vendor, "name", str(jc.vendor)) if jc.vendor_id else ""),
                "qty": qty,
                "used": used,
                "remaining": remaining,
                "unit_price": _pick_unit_price(jc),
                "uom": getattr(jc, "uom", "") or "",
            })

        ctx["rows"] = rows
        return ctx

    def post(self, request, *args, **kwargs):
        job = self._get_job()
        if not job:
            messages.error(request, "Job Order tidak valid.")
            return redirect("job:job_order_list")  # sesuaikan

        picked_ids = request.POST.getlist("pick")
        if not picked_ids:
            messages.error(request, "Pilih minimal 1 cost line.")
            return redirect(f"{reverse('shipments:vendor_booking_from_jobcost')}?job_order={job.id}")

        selected = list(
            JobCost.objects
            .filter(job_order=job, id__in=picked_ids, cost_type__requires_vendor=True)
            .exclude(vendor__isnull=True)
            .select_related("vendor", "cost_type")
        )
        if not selected:
            messages.error(request, "Cost line terpilih tidak valid.")
            return redirect(f"{reverse('shipments:vendor_booking_from_jobcost')}?job_order={job.id}")

        used_map = self._used_map_for_job(job)

        locked_vendor_id = selected[0].vendor_id
        locked_group = _get_cost_group_from_jobcost(selected[0])

        errors = []
        lines_payload = []

        for jc in selected:
            if jc.vendor_id != locked_vendor_id:
                errors.append("Vendor tidak konsisten. Pilih cost line dengan vendor yang sama.")
                break

            jc_group = _get_cost_group_from_jobcost(jc)
            if jc_group != locked_group:
                errors.append("Group tidak konsisten. Pilih cost line dengan cost_group yang sama.")
                break

            if not jc.cost_type_id:
                errors.append(f"Cost Type kosong pada JobCost #{jc.id}.")
                continue

            raw_qty = (request.POST.get(f"qty_{jc.id}", "") or "").strip()

            qty = jc.qty or Decimal("0")
            used = used_map.get(jc.id, Decimal("0"))
            remaining = qty - used

            # ✅ kalau user centang tapi qty kosong -> default allocate = remaining
            if raw_qty == "":
                alloc = remaining
            else:
                alloc = _to_decimal(raw_qty)

            if alloc <= 0:
                errors.append(f"Qty allocate harus > 0 untuk: {jc.cost_type.name}")
                continue

            if alloc > remaining:
                errors.append(f"Qty allocate melebihi remaining untuk: {jc.cost_type.name} (remaining {remaining})")
                continue


            qty = jc.qty or Decimal("0")
            used = used_map.get(jc.id, Decimal("0"))
            remaining = qty - used
            if alloc > remaining:
                errors.append(f"Qty allocate melebihi remaining untuk: {jc.cost_type.name} (remaining {remaining})")
                continue

            lines_payload.append((jc, alloc))

        if errors:
            for e in errors[:3]:
                messages.error(request, e)
            if len(errors) > 3:
                messages.error(request, f"({len(errors)-3} error lain)")
            return redirect(f"{reverse('shipments:vendor_booking_from_jobcost')}?job_order={job.id}")

        if not lines_payload:
            messages.error(request, "Tidak ada line valid untuk dibuat.")
            return redirect(f"{reverse('shipments:vendor_booking_from_jobcost')}?job_order={job.id}")

        vb = VendorBooking(
            job_order=job,
            vendor_id=locked_vendor_id,
            letter_type=_letter_type_from_mode(job),
            status="DRAFT",
            issued_date=timezone.localdate(),
            discount_amount=Decimal("0"),
        )
        vb.save()

        vb_lines = []
        for (jc, alloc) in lines_payload:
            unit_price = _pick_unit_price(jc)
            amount = (Decimal(alloc) * unit_price).quantize(Decimal("0.01"))

            vb_lines.append(VendorBookingLine(
                vendor_booking=vb,
                job_cost=jc,
                cost_type_id=jc.cost_type_id,
                cost_group=_get_cost_group_from_jobcost(jc),
                uom=getattr(jc, "uom", "") or "",
                qty=alloc,
                unit_price=unit_price,
                amount=amount,
            ))

        VendorBookingLine.objects.bulk_create(vb_lines)

        recompute_vendor_booking_totals(vb)

        edit_url = reverse("shipments:vendor_booking_edit", args=[vb.id])
        return redirect(f"{edit_url}?job_order={job.id}")


class VendorBookingConfirmView(LoginRequiredMixin, View):
    def post(self, request, pk):
        vb = get_object_or_404(
            VendorBooking.objects.prefetch_related("lines"),
            pk=pk
        )

        if vb.status != "DRAFT":
            messages.warning(request, "Vendor Booking sudah dikonfirmasi.")
            return redirect(f"{reverse('shipments:vendor_booking_edit', args=[vb.id])}?job_order={vb.job_order_id}")

        lines = list(vb.lines.all())
        if not lines:
            messages.error(request, "Tidak bisa confirm: belum ada line.")
            return redirect(f"{reverse('shipments:vendor_booking_edit', args=[vb.id])}?job_order={vb.job_order_id}")

        # ✅ VALIDASI AKAD: qty & harga wajib jelas
        bad = []
        for ln in lines:
            if (ln.qty or 0) <= 0:
                bad.append(f"Line #{ln.id}: qty kosong")
            if (ln.unit_price or 0) <= 0:
                bad.append(f"Line #{ln.id}: unit price kosong")
            if (ln.amount or 0) <= 0:
                bad.append(f"Line #{ln.id}: amount kosong")

        if bad:
            messages.error(request, "Tidak bisa confirm. Lengkapi qty & harga dulu.")
            for m in bad[:3]:
                messages.error(request, m)
            return redirect(f"{reverse('shipments:vendor_booking_edit', args=[vb.id])}?job_order={vb.job_order_id}")

        # pastikan totals header up-to-date
        recompute_vendor_booking_totals(vb)

        vb.status = "CONFIRMED"
        if hasattr(vb, "confirmed_at") and not vb.confirmed_at:
            vb.confirmed_at = timezone.now()

        vb.save()
        messages.success(request, "Confirmed ✅ (Issued internal). Siap dikirim ke vendor.")
        return redirect(f"{reverse('shipments:vendor_booking_edit', args=[vb.id])}?job_order={vb.job_order_id}")


class VendorBookingPrintView(LoginRequiredMixin, View):
    def get(self, request, pk):
        vb = get_object_or_404(
            VendorBooking.objects
            .select_related("job_order", "vendor")
            .prefetch_related("lines__job_cost", "lines__cost_type", "lines__taxes"),
            pk=pk
        )

        lt = (vb.letter_type or "").upper().strip()

        # pilih template
        if lt == "SI":
            tpl = "vendor_bookings/print/si.html"
        elif lt == "SLI":
            tpl = "vendor_bookings/print/sli.html"
        elif lt == "SO":
            tpl = "vendor_bookings/print/so.html"
        else:
            tpl = "vendor_bookings/print/wo.html"

        # ✅ Print boleh DRAFT, nanti template kasih watermark
        return render(request, tpl, {"vb": vb, "is_draft": (vb.status == "DRAFT")})



from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from shipments.forms.vendor_bookings import VendorBookingForm, VendorBookingLineFormSet
from shipments.models.vendor_bookings import VendorBooking
from shipments.services.vendor_booking_totals import recompute_vendor_booking_totals


class VendorBookingEditView(LoginRequiredMixin, View):
    template_name = "vendor_bookings/form.html"

    def get(self, request, pk):
        vb = get_object_or_404(
            VendorBooking.objects
            .select_related("job_order", "vendor", "currency")
            .prefetch_related("lines__cost_type", "lines__job_cost", "lines__taxes"),
            pk=pk
        )
        form = VendorBookingForm(instance=vb)
        formset = VendorBookingLineFormSet(instance=vb)

        totals = recompute_vendor_booking_totals(vb)  # biar header always sync (aman)
        return render(request, self.template_name, {
            "vb": vb,
            "form": form,
            "formset": formset,
            "totals": totals,
            "job_order_id": request.GET.get("job_order", vb.job_order_id),
        })

    def post(self, request, pk):
        vb = get_object_or_404(
            VendorBooking.objects
            .select_related("job_order", "vendor", "currency")
            .prefetch_related("lines__taxes"),
            pk=pk
        )

        # kalau sudah confirmed, jangan boleh edit
        if vb.status != "DRAFT":
            messages.warning(request, "Vendor Booking sudah CONFIRMED. Tidak bisa diedit.")
            return redirect(f"{reverse('shipments:vendor_booking_edit', args=[vb.id])}?job_order={vb.job_order_id}")

        form = VendorBookingForm(request.POST, instance=vb)
        formset = VendorBookingLineFormSet(request.POST, instance=vb)

        if not (form.is_valid() and formset.is_valid()):
            messages.error(request, "Ada error. Cek field merah.")
            return render(request, self.template_name, {
                "vb": vb,
                "form": form,
                "formset": formset,
                "totals": recompute_vendor_booking_totals(vb),
                "job_order_id": request.GET.get("job_order", vb.job_order_id),
            })

        with transaction.atomic():
            form.save()
            instances = formset.save()      # save line fields (qty/unit_price/uom)
            formset.save_m2m()             # penting untuk taxes M2M

            # hitung ulang amount line? (kalau model line tidak auto-save amount)
            # karena ini bukan bulk_create, save() terpanggil. Tapi jika amount tidak auto,
            # kita amanin dengan recompute totals saja.
            totals = recompute_vendor_booking_totals(vb)

        messages.success(request, "Tersimpan ✅. Silakan Print atau Confirm.")
      
        return redirect(f"{reverse('shipments:vendor_booking_edit', args=[vb.id])}?job_order={vb.job_order_id}")




class VendorBookingCreateView(LoginRequiredMixin, CreateView):
    model = VendorBooking
    form_class = VendorBookingForm
    template_name = "vendor_bookings/form.html"

    def post(self, request, *args, **kwargs):
        """
        FIX: field disabled / tidak ada input -> tidak terkirim di POST -> form invalid.
        Kita inject default values sebelum form di-validate.
        """
        data = request.POST.copy()  # mutable

        # 1) job_order wajib: ambil dari querystring kalau tidak ada di POST
        job_id = data.get("job_order") or request.GET.get("job_order") or request.GET.get("job_orders")
        if job_id and not data.get("job_order"):
            data["job_order"] = str(job_id)

        # 2) issued_date default hari ini
        if not data.get("issued_date"):
            data["issued_date"] = timezone.now().date().isoformat()

        # 3) discount_amount default 0
        if not data.get("discount_amount"):
            data["discount_amount"] = "0"

        # 4) letter_type default TRUCK_TO
        if not data.get("letter_type"):
            data["letter_type"] = "TRUCK_TO"

        # 5) idr_rate default 1 (biar aman)
        if not data.get("idr_rate"):
            data["idr_rate"] = "1"

        # bikin form dari data yang sudah lengkap
        form = self.get_form(self.get_form_class())
        form.data = data

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        booking = form.save(commit=False)
        booking.status = VendorBooking.ST_DRAFT
        booking.created_by = self.request.user
        booking.save()
        self.object = booking
        return redirect("shipments:vendor_booking_edit", pk=booking.pk)



class VendorBookingListView(LoginRequiredMixin, ListView):
    model = VendorBooking
    template_name = "vendor_bookings/list.html"
    context_object_name = "items"
    paginate_by = 30

    def get_queryset(self):
        qs = (
            VendorBooking.objects
            .select_related("job_order", "vendor", "currency")
            .order_by("-id")
        )

        job_order_id = (self.request.GET.get("job_order") or "").strip()
        status = (self.request.GET.get("status") or "").strip().upper()
        vendor_q = (self.request.GET.get("vendor") or "").strip()

        if job_order_id.isdigit():
            qs = qs.filter(job_order_id=int(job_order_id))

        if status in ("DRAFT", "CONFIRMED", "CANCELLED", "COMPLETED"):
            qs = qs.filter(status=status)

        if vendor_q:
            # cocok untuk Partner name/code (sesuaikan field vendor)
            qs = qs.filter(
                Q(vendor__name__icontains=vendor_q) |
                Q(vendor__code__icontains=vendor_q)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # dropdown job order untuk "Create from JobCost"
        ctx["job_orders"] = JobOrder.objects.order_by("-id")[:200]  # batasi biar ringan

        # keep filter values
        ctx["f_job_order"] = (self.request.GET.get("job_order") or "").strip()
        ctx["f_status"] = (self.request.GET.get("status") or "").strip().upper()
        ctx["f_vendor"] = (self.request.GET.get("vendor") or "").strip()

        return ctx

class VendorUpdateView(LoginRequiredMixin, UpdateView):
    """
    Vendor Booking Review/Edit (Header + Lines).
    - Tidak boleh add/remove line manual (formset extra=0, can_delete=False)
    - DRAFT bisa edit
    - CONFIRMED read-only
    """
    model = VendorBooking
    form_class = VendorBookingForm
    template_name = "vendor_bookings/form.html"
    context_object_name = "vb"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        # kalau confirmed: blok edit via POST
        if request.method == "POST" and self.object.status != "DRAFT":
            messages.warning(request, "Vendor Booking sudah CONFIRMED. Tidak bisa diedit.")
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["instance"] = self.object
        return kw

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # formset untuk lines
        if self.request.method == "POST":
            ctx["formset"] = VendorBookingLineFormSet(self.request.POST, instance=self.object)
        else:
            ctx["formset"] = VendorBookingLineFormSet(instance=self.object)

        # keep job_order param buat tombol back/redirect
        ctx["job_order_id"] = self.request.GET.get("job_order", self.object.job_order_id)

        # sync totals (aman dipanggil GET)
        ctx["totals"] = recompute_vendor_booking_totals(self.object)
        first_line = self.object.lines.first()
        ctx["vb_group"] = (first_line.cost_group if first_line else "")
        ctx["letter_type"] = (self.object.letter_type or "")
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]

        if not formset.is_valid():
            messages.error(self.request, "Ada error pada lines. Cek field merah.")
            return self.form_invalid(form)

        with transaction.atomic():
            vb = form.save()

            # save formset + m2m taxes
            formset.instance = vb
            formset.save()
            if hasattr(formset, "save_m2m"):
                formset.save_m2m()

            # update totals header (wht_amount + total_amount)
            recompute_vendor_booking_totals(vb)

        messages.success(self.request, "Tersimpan ✅. Silakan Print atau Confirm.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        job_id = self.request.GET.get("job_order", self.object.job_order_id)
        return f"{reverse('shipments:vendor_booking_edit', args=[self.object.id])}?job_order={job_id}"
