from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.shortcuts import get_object_or_404

from job.models.job_orders import JobOrder

from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine
from django.views.generic import DetailView
from shipments.forms.vendor_bookings import VendorBookingForm
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import View

from shipments.models.vendor_bookings import VendorBooking
from shipments.views.vendor_booking_base import VendorBookingObjectMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, View
from django.http import JsonResponse, HttpResponseForbidden

from job.models.costs import JobCostType


# views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from job.services.job_cost_vb import recalc_job_cost_vb

from django.db.models import Sum
from shipments.models.vendor_bookings import VendorBookingLine  # ✅ sesuaikan kalau path beda
from django.db.models import Max




def build_cost_type_map():
    """
    Mapping cost_type_id -> meta untuk JS (SEA / AIR / TRUCK)
    """
    qs = JobCostType.objects.filter(is_active=True).values(
        "id", "code", "name", "cost_group"
    )

    result = {}
    for r in qs:
        code = (r["code"] or "").upper()
        group = (r["cost_group"] or "").upper()
        name = (r["name"] or "").upper()

        service_type = ""
        if "SEA" in group or "SEA" in code or "SEA" in name:
            service_type = "SEA"
        elif "AIR" in group or "AIR" in code or "AIR" in name:
            service_type = "AIR"
        elif "TRUCK" in group or "INLAND" in group or "TRUCK" in code or "INLAND" in name:
            service_type = "TRUCK"

        result[str(r["id"])] = {
            "id": r["id"],
            "code": r["code"],
            "name": r["name"],
            "cost_group": r["cost_group"],
            "service_type": service_type,
        }

    return result



def build_job_vendor_cost_summary(job):
    """
    Summary vendor-required JobCost vs booked VendorBookingLines (per cost_type).
    Tanpa soft delete.
    """
    # 1) baseline job costs yang require vendor
    job_costs = (
        job.job_costs
          .select_related("cost_type", "currency")
          .filter(cost_type__requires_vendor=True)
          .order_by("cost_type__sort_order", "id")
    )

    # 2) booked by cost_type dari semua vendor booking lines pada job ini

    booked_qs = (
        VendorBookingLine.objects
        .filter(vendor_booking__job_order=job, is_active=True)
        .values("cost_type_id")
        .annotate(
            booked_qty=Sum("qty"),
            booked_amount=Sum("amount"),
        )
    )
    booked_map = {r["cost_type_id"]: r for r in booked_qs}

    # 3) merge
    summary = []
    for jc in job_costs:
        plan_amount = (jc.qty or 0) * (jc.price or 0)
        plan_amount_idr = plan_amount * (jc.rate or 1)

        b = booked_map.get(jc.cost_type_id, {})
        booked_qty = b.get("booked_qty") or 0
        booked_amount = b.get("booked_amount") or 0

        status = "Not booked"
        if booked_amount:
            status = "Partially booked"
        if plan_amount and booked_amount >= plan_amount:
            status = "Fully booked"

        summary.append({
            "cost_type_id": jc.cost_type_id,
            "cost_type_name": jc.cost_type.name,
            "job_qty": jc.qty,
            "job_price": jc.price,
            "job_currency": (jc.currency.code if jc.currency else ""),
            "job_rate": jc.rate,
            "plan_amount": plan_amount,
            "plan_amount_idr": plan_amount_idr,
            "booked_qty": booked_qty,
            "booked_amount": booked_amount,
            "status": status,
        })

    return summary



from django.db import transaction

# pastikan import JobCost ada (di file om belum ada)
from job.models.costs import JobCost


@transaction.atomic
def sync_vendor_booking_lines(vb):
    """
    BUAT/UPDATE lines VendorBooking agar 100% mirror JobCost.
    - Tidak ada add/remove manual.
    - Lines dibuat berdasarkan: job_order + booking_group + requires_vendor.
    - Jika vb.vendor ada -> filter jobcost berdasarkan vendor tsb (PO per vendor).
    """

    # guard: wajib job_order + booking_group
    if not vb.job_order_id or not vb.booking_group:
        return {"ok": False, "added": 0, "updated": 0, "disabled": 0, "reason": "missing job_order/booking_group"}

    # 1) ambil jobcost yang relevan
    qs = (
        JobCost.objects
        .select_related("cost_type", "currency", "vendor")
        .filter(
            job_order_id=vb.job_order_id,
            is_active=True,
            cost_type__requires_vendor=True,
            cost_type__cost_group=vb.booking_group,
        )
        .order_by("cost_type__sort_order", "id")
    )

    # PO per vendor (recommended)
    if vb.vendor_id:
        qs = qs.filter(vendor_id=vb.vendor_id)

    job_costs = list(qs)

    # 2) existing lines map by job_cost_id
    existing_lines = {ln.job_cost_id: ln for ln in vb.lines.all()}

    added = 0
    updated = 0
    disabled = 0
    keep_ids = set()

    line_no = 1
    for jc in job_costs:
        keep_ids.add(jc.id)

        ln = existing_lines.get(jc.id)
        is_new = ln is None
        if is_new:
            ln = VendorBookingLine(vendor_booking=vb, job_cost=jc)

        # 3) sync snapshot dari jobcost -> line
        # NOTE: sesuaikan field JobCost om:
        qty = getattr(jc, "qty", None) or 1
        price = getattr(jc, "price", None) or 0
        rate = getattr(jc, "rate", None) or 1

        ln.line_no = line_no
        ln.cost_type_id = jc.cost_type_id
        ln.description = (getattr(jc, "description", "") or jc.cost_type.name)[:255]
        ln.qty = qty
        ln.unit_price = price
        ln.currency_id = getattr(jc, "currency_id", None) or vb.currency_id
        ln.idr_rate = rate
        ln.amount = qty * price
        ln.is_active = True

        ln.save()
        if is_new:
            added += 1
        else:
            updated += 1

        line_no += 1

    # 4) disable lines yang jobcost-nya sudah tidak relevan
    for jc_id, ln in existing_lines.items():
        if jc_id not in keep_ids and ln.is_active:
            ln.is_active = False
            ln.save(update_fields=["is_active"])
            disabled += 1

    # 5) recalc JobCost VB (kalau om pakai service ini)
    try:
        for jc in job_costs:
            recalc_job_cost_vb(jc)
    except Exception:
        # biarkan silent supaya UX tidak pecah, nanti kita rapihin log
        pass

    from django.utils import timezone

    vb.last_synced_at = timezone.now()
    vb.save(update_fields=["last_synced_at"])

    return {"ok": True, "added": added, "updated": updated, "disabled": disabled}



class VendorBookingListView(LoginRequiredMixin, ListView):
    template_name = "vendor_bookings/list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        self.job = get_object_or_404(JobOrder, pk=self.kwargs["job_id"])
        return (
            VendorBooking.objects
            .filter(job_order=self.job)
            .select_related("vendor", "currency", "job_order")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["job"] = self.job
       
        return ctx



class VendorBookingDetailView(LoginRequiredMixin, DetailView):
    model = VendorBooking
    template_name = "vendor_bookings/detail.html"
    context_object_name = "booking"

    def get_queryset(self):
        return (
            VendorBooking.objects
            .select_related("vendor", "currency", "job_order")
            .prefetch_related("lines")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["job"] = self.object.job_order
        ctx["lines"] = self.object.lines.all()
        return ctx


from django.utils import timezone


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


class VendorBookingUpdateView(LoginRequiredMixin, UpdateView):
    model = VendorBooking
    form_class = VendorBookingForm
    template_name = "vendor_bookings/form.html"
    

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
         # DEBUG
        print("DEBUG VB EDIT pk =", self.object.pk)
        print("DEBUG template =", getattr(self, "template_name", None))
        print("DEBUG related lines count =", self.object.lines.count())
        print("DEBUG active lines count =", self.object.lines.filter(is_active=True).count())


        ctx["job"] = self.object.job_order
        ctx["job_cost_summary"] = build_job_vendor_cost_summary(self.object.job_order)
        ctx["lines"] = self.object.lines.filter(is_active=True).order_by("line_no")
        return ctx

    def form_valid(self, form):
        if self.object.status != VendorBooking.ST_DRAFT:
            messages.error(self.request, "Booking sudah CONFIRMED/CANCELLED, tidak bisa diubah.")
            return redirect("shipments:vendor_booking_edit", pk=self.object.pk)

        self.object = form.save()
        res = sync_vendor_booking_lines(self.object)

        messages.success(self.request, f"✅ Synced from JobCost: +{res['added']}, ~{res['updated']}, -{res['disabled']}")
        return redirect("shipments:vendor_booking_edit", pk=self.object.pk)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.object and self.object.status != VendorBooking.ST_DRAFT:
            for f in form.fields.values():
                f.disabled = True
        return form


class VendorBookingSendView(VendorBookingObjectMixin, View):
    def post(self, request, pk):
        b = self.get_object()
        if b.status != VendorBooking.ST_DRAFT:
            return HttpResponseForbidden("Hanya DRAFT yang bisa dikirim.")
        # TODO: set sent_at / status if you have it
        messages.success(request, "✅ Booking marked as sent (still DRAFT unless you add status).")
        return redirect("shipments:vendor_booking_detail", pk=b.pk)


class VendorBookingConfirmView(VendorBookingObjectMixin, View):
    def post(self, request, pk):
        vb = self.get_object()
        if vb.status != VendorBooking.ST_DRAFT:
            return HttpResponseForbidden("Hanya DRAFT yang bisa confirm.")
        if not b.vendor_id:
            return HttpResponseForbidden("Vendor wajib diisi sebelum confirm.")
        
        sync_vendor_booking_lines(vb)
        
        vb.status = VendorBooking.ST_CONFIRMED
        vb.save(update_fields=["status"])
        messages.success(request, "✅ Booking confirmed.")
        return redirect("shipments:vendor_booking_detail", pk=b.pk)


class VendorBookingCompleteView(VendorBookingObjectMixin, View):
    def post(self, request, pk):
        b = self.get_object()
        if b.status != VendorBooking.ST_CONFIRMED:
            return HttpResponseForbidden("Hanya CONFIRMED yang bisa complete.")
        # kalau om punya ST_COMPLETED, tambahkan. Kalau tidak, bisa tetap CONFIRMED + flag complete_at
        messages.success(request, "✅ Booking completed (implement status/flag sesuai kebutuhan).")
        return redirect("shipments:vendor_booking_detail", pk=b.pk)


class VendorBookingCancelView(VendorBookingObjectMixin, View):
    def post(self, request, pk):
        b = self.get_object()
        if b.status == VendorBooking.ST_CANCELLED:
            return redirect("shipments:vendor_booking_detail", pk=b.pk)
        b.status = VendorBooking.ST_CANCELLED
        b.save(update_fields=["status"])
        messages.success(request, "✅ Booking cancelled.")
        return redirect("shipments:vendor_booking_detail", pk=b.pk)



@require_GET
@login_required
def vb_job_costs_json(request):
    job_order_id = request.GET.get("job_order")
    booking_group = (request.GET.get("booking_group") or "").strip()

    if not job_order_id or not booking_group:
        return JsonResponse({"ok": False, "error": "job_order dan booking_group wajib."}, status=400)

    # adjust import path
    from job.models.job_orders import JobOrder
    job = JobOrder.objects.filter(pk=job_order_id).first()
    if not job:
        return JsonResponse({"ok": False, "error": "Job Order tidak ditemukan."}, status=404)

    qs = (
        job.job_costs.filter(is_active=True)
        .select_related("cost_type")
        .order_by("cost_type__sort_order", "id")
        .filter(cost_type__cost_group=booking_group)
    )

    items = []
    for jc in qs:
        ct = jc.cost_type
        items.append({
            "job_cost_id": jc.id,
            "cost_type_id": ct.id,
            "cost_type_name": ct.name,
            "description": (getattr(jc, "description", "") or ct.name),
            "qty": float(getattr(jc, "qty", 1) or 1),
            "uom": getattr(jc, "uom", "") or "",
        })

    return JsonResponse({"ok": True, "items": items})



class VendorBookingSyncView(LoginRequiredMixin, View):
    def post(self, request, pk):
        b = get_object_or_404(VendorBooking, pk=pk)

        if b.status != VendorBooking.ST_DRAFT:
            messages.error(request, "Booking locked. Hanya DRAFT yang bisa sync.")
            return redirect("shipments:vendor_booking_edit", pk=b.pk)

        res = sync_vendor_booking_lines(b)
        if res.get("ok"):
            messages.success(
                request,
                f"✅ Sync OK: +{res['added']} new, ~{res['updated']} updated, -{res['disabled']} disabled."
            )
        else:
            messages.error(request, "Sync gagal. Pastikan Job Order & Booking Group sudah benar.")

        return redirect("shipments:vendor_booking_edit", pk=b.pk)

class VendorBookingPrintView(LoginRequiredMixin, DetailView):
    model = VendorBooking
    template_name = "vendor_bookings/print/print_dispatch.html"  # dispatcher template

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # ✅ only confirmed (biar dokumen final)
        if self.object.status != VendorBooking.ST_CONFIRMED:
            return HttpResponseForbidden("Print hanya untuk booking CONFIRMED.")

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        b = self.object
        ctx["job"] = b.job_order
        ctx["lines"] = b.lines.filter(is_active=True).order_by("line_no", "id")

        # header_json dict (kalau null -> {})
        header = b.header_json or {}
        ctx["header"] = header

        # human title
        ctx["doc_title"] = {
            "SEA_SI": "Shipping Instruction",
            "AIR_SLI": "Shipping Line Instruction",
            "TRUCK_TO": "Trucking / Service Order",
            "WORKING_ORDER": "Working Order",
        }.get(b.letter_type, "Vendor Document")

        # pilih template berdasarkan letter_type
        ctx["print_template"] = {
            "SEA_SI": "vendor_bookings/print/sea_si.html",
            "AIR_SLI": "vendor_bookings/print/air_sli.html",
            "TRUCK_TO": "vendor_bookings/print/truck_to.html",
            "WORKING_ORDER": "vendor_bookings/print/working_order.html",
        }.get(b.letter_type, "vendor_bookings/print/generic.html")

        return ctx







#############################################################################################

from decimal import Decimal
from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView

from job.models.job_orders import JobOrder
from job.models.costs import JobCost
from core.models.currencies import Currency
from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine


def _safe_decimal(v, default="0"):
    try:
        if v in (None, ""):
            return Decimal(default)
        return Decimal(str(v))
    except Exception:
        return Decimal(default)


def _jobcost_unit_price(jc):
    # sesuaikan nama field JobCost om: price / unit_price
    return _safe_decimal(getattr(jc, "price", None) or getattr(jc, "unit_price", None) or 0, "0")


def _jobcost_uom(jc):
    return getattr(jc, "uom", "") or ""


def _group_to_letter_type(cost_group: str) -> str:
    g = (cost_group or "").upper()
    if g == "SEA":
        return "SEA_SI"
    if g == "AIR":
        return "AIR_SLI"
    if g in ("INLAND", "TRUCK", "TRUCKING"):
        return "TRUCK_TO"
    return "WORKING_ORDER"


class VendorBookingFromJobCostWizardView(LoginRequiredMixin, View):
    """
    STEP 2:
    Wizard (server-rendered): pilih cost lines yang masih remaining > 0
    Rule:
      - 1 VBO = 1 vendor
      - 1 VBO = 1 cost_group
      - letter_type otomatis dari cost_group
      - remaining dihitung dari SUM(VBLine.qty) per job_cost_id
    """
    template_name = "vendor_bookings/from_jobcost.html"

    def get(self, request):
        job_id = request.GET.get("job_order") or request.GET.get("job_orders")
        if not job_id:
            messages.error(request, "Missing job_order. Use ?job_order=ID")
            return redirect("shipments:vendor_booking_list")

        job = get_object_or_404(JobOrder, pk=job_id)

        jc_qs = (
            JobCost.objects
            .filter(job_order=job, cost_type__requires_vendor=True)
            .select_related("vendor", "cost_type", "currency")
            .order_by("cost_type__sort_order", "id")
        )
        if hasattr(JobCost, "is_active"):
            jc_qs = jc_qs.filter(is_active=True)

        # booked qty per job_cost
        booked = (
            VendorBookingLine.objects
            .filter(vendor_booking__job_order=job, is_active=True, job_cost__isnull=False)
            .values("job_cost_id")
            .annotate(booked_qty=Sum("qty"))
        )
        booked_map = {r["job_cost_id"]: (r["booked_qty"] or Decimal("0")) for r in booked}

        items = []
        for jc in jc_qs:
            # wajib ada vendor
            if not getattr(jc, "vendor_id", None):
                continue

            total_qty = _safe_decimal(getattr(jc, "qty", None), "0")
            used_qty = _safe_decimal(booked_map.get(jc.id, 0), "0")
            remaining = total_qty - used_qty
            if remaining <= 0:
                continue

            unit_price = _jobcost_unit_price(jc)
            cost_group = getattr(getattr(jc, "cost_type", None), "cost_group", "") or ""
            items.append({
                "id": jc.id,
                "vendor_id": jc.vendor_id,
                "vendor_name": getattr(getattr(jc, "vendor", None), "name", "") or "",
                "cost_type_name": getattr(getattr(jc, "cost_type", None), "name", "") or "",
                "cost_group": cost_group,
                "desc": getattr(jc, "description", "") or "",
                "qty_total": total_qty,
                "qty_used": used_qty,
                "qty_remaining": remaining,
                "uom": _jobcost_uom(jc),
                "unit_price": unit_price,
                "currency": getattr(getattr(jc, "currency", None), "code", "") or "",
            })

        # group by (vendor, group)
        grouped = OrderedDict()
        for it in items:
            key = (it["vendor_id"], it["vendor_name"], it["cost_group"])
            grouped.setdefault(key, []).append(it)

        return render(request, self.template_name, {"job": job, "groups": grouped})

    def post(self, request):
        job_id = request.POST.get("job_order") or request.POST.get("job_orders")
        if not job_id:
            messages.error(request, "Missing job_order.")
            return redirect("shipments:vendor_booking_list")

        job = get_object_or_404(JobOrder, pk=job_id)

        selected_ids = request.POST.getlist("jc")
        if not selected_ids:
            messages.error(request, "Pilih minimal 1 cost line.")
            return redirect(f"{request.path}?job_order={job.id}")

        jcs = list(
            JobCost.objects
            .filter(job_order=job, id__in=selected_ids, cost_type__requires_vendor=True)
            .select_related("vendor", "cost_type", "currency")
        )

        vendor_ids = {jc.vendor_id for jc in jcs if jc.vendor_id}
        if len(vendor_ids) != 1:
            messages.error(request, "1 VBO hanya untuk 1 vendor. Pilih cost line vendor yang sama.")
            return redirect(f"{request.path}?job_order={job.id}")

        group_set = {getattr(jc.cost_type, "cost_group", "") or "" for jc in jcs}
        if len(group_set) != 1:
            messages.error(request, "1 VBO hanya untuk 1 cost group. Pilih cost line group yang sama.")
            return redirect(f"{request.path}?job_order={job.id}")

        vendor_id = list(vendor_ids)[0]
        booking_group = list(group_set)[0]
        letter_type = _group_to_letter_type(booking_group)

        # booked map (untuk remaining)
        booked = (
            VendorBookingLine.objects
            .filter(vendor_booking__job_order=job, is_active=True, job_cost__in=jcs)
            .values("job_cost_id")
            .annotate(booked_qty=Sum("qty"))
        )
        booked_map = {r["job_cost_id"]: (r["booked_qty"] or Decimal("0")) for r in booked}

        # create VB (numbering auto by model.save)
        vb = VendorBooking(
            job_order=job,
            vendor_id=vendor_id,
            booking_group=booking_group,
            letter_type=letter_type,
            discount_amount=Decimal("0"),
            issued_date=timezone.now().date(),
        )

        # default currency IDR + rate 1 (biar aman)
        cur_idr = Currency.objects.filter(code="IDR").first()
        if cur_idr:
            vb.currency = cur_idr
            vb.idr_rate = Decimal("1")

        vb.status = VendorBooking.ST_DRAFT
        vb.created_by = request.user
        vb.save()

        created = 0
        for jc in jcs:
            total_qty = _safe_decimal(getattr(jc, "qty", None), "0")
            used_qty = _safe_decimal(booked_map.get(jc.id, 0), "0")
            remaining = total_qty - used_qty
            if remaining <= 0:
                continue

            req_qty = _safe_decimal(request.POST.get(f"qty_{jc.id}"), str(remaining))
            if req_qty <= 0:
                continue
            if req_qty > remaining:
                messages.error(request, f"Qty terlalu besar untuk costline #{jc.id}. Remaining={remaining}.")
                vb.delete()
                return redirect(f"{request.path}?job_order={job.id}")

            unit_price = _jobcost_unit_price(jc)
            amount = (req_qty or 0) * (unit_price or 0)

            VendorBookingLine.objects.create(
                vendor_booking=vb,
                job_cost=jc,
                cost_type=jc.cost_type,
                description=getattr(jc, "description", "") or jc.cost_type.name,
                qty=req_qty,
                uom=_jobcost_uom(jc),
                unit_price=unit_price,
                amount=amount,
                is_active=True,
            )
            created += 1

        messages.success(request, f"✅ VBO created: {vb.vb_number} / {vb.letter_number} (lines: {created})")
        return redirect("shipments:vendor_booking_edit", pk=vb.pk)


class VendorBookingConfirmView(LoginRequiredMixin, View):
    # STEP 3 Confirm
    def post(self, request, pk):
        vb = get_object_or_404(VendorBooking, pk=pk)

        if vb.status != VendorBooking.ST_DRAFT:
            messages.error(request, "Vendor Booking sudah dikunci.")
            return redirect("shipments:vendor_booking_edit", pk=vb.pk)

        if vb.lines.filter(is_active=True).count() == 0:
            messages.error(request, "Tidak bisa confirm tanpa booking line.")
            return redirect("shipments:vendor_booking_edit", pk=vb.pk)

        vb.status = VendorBooking.ST_CONFIRMED
        vb.save(update_fields=["status"])

        messages.success(request, "Vendor Booking berhasil dikonfirmasi.")
        return redirect("shipments:vendor_booking_edit", pk=vb.pk)


class VendorBookingPrintView(LoginRequiredMixin, DetailView):
    # STEP 3 Print
    model = VendorBooking

    def get_template_names(self):
        vb = self.object
        # mapping template by letter_type
        lt = (vb.letter_type or "").lower()
        # default fallback
        if lt in ("sea_si", "si"):
            tpl = "si.html"
        elif lt in ("air_sli", "sli"):
            tpl = "sli.html"
        elif lt in ("truck_to", "so"):
            tpl = "so.html"
        else:
            tpl = "wo.html"
        return [f"vendor_bookings/print/{tpl}"]
