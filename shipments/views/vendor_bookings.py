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
from job.models.job_costs import JobCost
from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine
from shipments.services.vendor_booking_totals import recompute_vendor_booking_totals
from django.views.generic import ListView
from django.views.generic import ListView, CreateView, DetailView, UpdateView, View
import shipments.services.vendor_booking_totals as vbt

from shipments.utils.heading import get_vendor_booking_heading
from django.db import transaction

from shipments.forms.vendor_bookings import VendorBookingForm, VendorBookingLineFormSet
from shipments.utils.heading import get_vendor_booking_heading

from shipments.services.vendor_booking_calc import calc_line_amount, calc_booking_totals
import inspect





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
                "unit_price": (jc.actual_amount if getattr(jc, "actual_amount", 0) else jc.est_amount) or Decimal("0"), 
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

        # ambil cost_group dari jobcost pertama (wizard sudah validasi semua sama)
        
        # ambil cost_group dari jobcost pertama (wizard sudah validasi semua sama)
        first_jc = lines_payload[0][0]  # (jc, alloc)
       # cg = (getattr(first_jc, "cost_group", "") or "").upper().strip()
        cg = _get_cost_group_from_jobcost(first_jc)  # ✅ ambil dari cost_type.cost_group


        vb = VendorBooking(
            job_order=job,
            vendor_id=locked_vendor_id,
            status="DRAFT",
            discount_amount=Decimal("0"),
        )
        vb.save()

        def _jc_price(jc):
            # sumber harga dari JobCost (sesuaikan kalau field om beda)
            val = getattr(jc, "actual_amount", None)
            if not val or Decimal(val or 0) == 0:
                val = getattr(jc, "est_amount", None)
            return Decimal(val or 0)

        vb_lines = []
        for (jc, alloc) in lines_payload:
            unit_price = _jc_price(jc)

            # qty di line tetap alloc (untuk tracking used/remaining),
            # tapi amount JANGAN bikin unit_price ketimpa oleh recompute nanti
            qty = Decimal(alloc or 0)
            amount = (qty * unit_price).quantize(Decimal("0.01"))

            desc = (jc.description if hasattr(jc, "description") else "") or ""
            if not desc and jc.cost_type_id:
                desc = jc.cost_type.name  # fallback

            uom_id = jc.cost_type.uom_id if jc.cost_type_id else None
            vb_lines.append(VendorBookingLine(
                vendor_booking=vb,
                job_cost=jc,
                cost_type_id=jc.cost_type_id,
                cost_group=_get_cost_group_from_jobcost(jc),
                uom_id= uom_id,
                qty=qty,
                unit_price=unit_price,
                amount=amount,
                description=desc,
            ))

        VendorBookingLine.objects.bulk_create(vb_lines)

        # sementara comment dulu untuk isolasi bug unit_price jadi 1
        # recompute_vendor_booking_totals(vb)

        update_url = reverse("shipments:vendor_booking_update", args=[vb.id])
        return redirect(f"{update_url}?job_order={job.id}")



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

            
        # 3) discount_amount default 0
        if not data.get("discount_amount"):
            data["discount_amount"] = "0"

        
        # 5) idr_rate default 1 (biar aman)
        if not data.get("idr_rate"):
            data["idr_rate"] = "1"

        # bikin form dari data yang sudah lengkap
        form = self.get_form(self.get_form_class())
        form.data = data

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

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


from decimal import Decimal
from core.models.taxes import Tax  # atau lokasi Tax yang benar di project kamu

def _build_tax_map():
    qs = Tax.objects.filter(is_active=True).only("id", "rate", "is_withholding")
    return {
        str(t.id): {
            "rate": float(t.rate or Decimal("0")),
            "is_withholding": bool(t.is_withholding),
        }
        for t in qs
    }

class VendorBookingUpdateView(View):
    template_name = "vendor_bookings/form.html"

    # ---------- small helpers ----------
    def get_object(self, pk):
        return get_object_or_404(VendorBooking, pk=pk)

    
    def _success_url(self, request, vb: VendorBooking):
        job_id = request.GET.get("job_order", vb.job_order_id)
        return f"{reverse('shipments:vendor_booking_update', args=[vb.pk])}?job_order={job_id}"

    def _build_ctx(self, vb, form, formset, job_id=None):
        ctx = {
            "vb": vb,
            "form": form,
            "formset": formset,
            "totals": calc_booking_totals(vb),

        }
        if job_id:
            ctx["job_order_id"] = job_id
        return ctx

    def _render_with_debug(self, request, vb, ctx, note=""):
        resp = render(request, self.template_name, ctx)
        src = inspect.getsourcefile(self.__class__) or "unknown"
        mode = getattr(getattr(vb, "job_order", None), "mode", None)

   
        return resp

    # ---------- GET ----------
    def get(self, request, pk):
        vb = self.get_object(pk)
       
        form = VendorBookingForm(instance=vb)
        formset = VendorBookingLineFormSet(instance=vb, prefix="lines")

        job_id = request.GET.get("job_order", vb.job_order_id)
        ctx = self._build_ctx(vb, form, formset, job_id=job_id)
        return self._render_with_debug(request, vb, ctx, note="(GET)")

    # ---------- POST ----------
    @transaction.atomic
    def post(self, request, pk):
        vb = self.get_object(pk)
       
        if vb.status != "DRAFT":
            messages.warning(request, "Vendor Booking sudah CONFIRMED. Tidak bisa diedit.")
            return redirect(self._success_url(request, vb))

        # ✅ KUNCI job_order_id dari DB langsung (anti vb.job_order_id kebaca NULL)
        db_job_id = VendorBooking.objects.filter(pk=pk).values_list("job_order_id", flat=True).first()
        if not db_job_id:
            messages.error(request, "Data Vendor Booking rusak: job_order kosong di DB.")
            return redirect(self._success_url(request, vb))

        form = VendorBookingForm(request.POST, instance=vb)
        formset = VendorBookingLineFormSet(request.POST, instance=vb, prefix="lines")

        if not (form.is_valid() and formset.is_valid()):
            messages.error(request, "Ada error. Cek input merah.")
            job_id = request.GET.get("job_order", db_job_id)
            ctx = self._build_ctx(vb, form, formset, job_id=job_id)
            return self._render_with_debug(request, vb, ctx, note="(POST invalid)")

        # ===== SAVE HEADER (commit=False + lock mandatory fields) =====
        booking = form.save(commit=False)

        # ✅ lock mandatory fields
        booking.job_order_id = db_job_id
    
        # fallback header aman
        if booking.discount_amount in (None, ""):
            booking.discount_amount = Decimal("0")
        if booking.wht_rate in (None, ""):
            booking.wht_rate = Decimal("0")
       
        booking.status = VendorBooking.ST_DRAFT
        booking.save()

        # ===== SAVE LINES + TAXES =====
        formset.instance = booking

        lines = formset.save(commit=False)
        for ln in lines:
            ln.vendor_booking = booking  # penting biar konsisten
            ln.amount = calc_line_amount(ln.qty, ln.unit_price)
            ln.save()

        # kalau suatu saat can_delete=True
        for obj in getattr(formset, "deleted_objects", []):
            obj.delete()

        # taxes M2M
        formset.save_m2m()

        # ===== RECOMPUTE TOTALS (tax + wht + total) =====
        vbt.recompute_vendor_booking_totals(booking)

        messages.success(request, "Tersimpan ✅")
        return redirect(self._success_url(request, booking))
    
    
    def _build_ctx(self, vb, form, formset, job_id=None):
            
        ctx = {
            "vb": vb,
            "form": form,
            "formset": formset,
            "totals": calc_booking_totals(vb),

            
            # ✅ INI yang bikin helper kepanggil
            "tax_map": _build_tax_map(),

        
        }
        if job_id:
            ctx["job_order_id"] = job_id
        return ctx



