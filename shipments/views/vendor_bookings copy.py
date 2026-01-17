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
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from shipments.views.vendor_booking_lines import VendorBookingLineDetailsView
from django.urls import reverse
from shipments.forms.vendor_bookings import VendorBookingLineFormSet

from job.models.costs import JobCostType
from core.models.taxes import Tax
from core.models.uoms import UOM


# views.py
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from job.services.job_cost_vb import recalc_job_cost_vb




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


from django.db.models import Sum, F, DecimalField, ExpressionWrapper



class VendorBookingBaseMixin:
    model = VendorBooking
    form_class = VendorBookingForm
    template_name = "shipments/vendor_booking_form.html"

    def get_success_url(self):
        return reverse_lazy("shipments:vendor_booking_edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["lines_formset"] = VendorBookingLineFormSet(self.request.POST, instance=self.object)
        else:
            ctx["lines_formset"] = VendorBookingLineFormSet(instance=self.object)

        # ✅ untuk template row dynamic add
        ctx["empty_line_form"] = ctx["lines_formset"].empty_form
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        fs = ctx["lines_formset"]

        self.object = form.save(commit=True)

        if fs.is_valid():
            fs.instance = self.object
            fs.save()

            job_cost_ids = (
                self.object.lines
                .filter(job_cost__isnull=False)
                .values_list("job_cost_id", flat=True)
                .distinct()
            )

            for jc in JobCost.objects.filter(id__in=job_cost_ids):
                recalc_job_cost_vb(jc)


            return redirect(self.get_success_url())

        return self.render_to_response(self.get_context_data(form=form))



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
    from shipments.models.vendor_bookings import VendorBookingLine  # ✅ sesuaikan kalau path beda

    booked_qs = (
        VendorBookingLine.objects
          .filter(booking__job_order=job)
          .values("cost_type_id")
          .annotate(
              booked_qty=Sum("qty"),
              booked_amount=Sum(
                  ExpressionWrapper(
                      F("qty") * F("unit_price"),
                      output_field=DecimalField(max_digits=18, decimal_places=2),
                  )
              ),
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



class VendorBookingCreateView(LoginRequiredMixin, CreateView):
    model = VendorBooking
    form_class = VendorBookingForm
    template_name = "vendor_bookings/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.job = self.get_selected_job()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        booking = form.save(commit=False)
        booking.job_order = self.job  # sekarang sudah terisi dari dispatch()
        booking.status = VendorBooking.ST_DRAFT
        booking.created_by = self.request.user
        booking.save()
        self.object = booking  # pastikan self.object ada untuk formset instance
        return super().form_valid(form)
        
    def get_selected_job(self):
        job_id = self.request.POST.get("job_order") or self.request.GET.get("job_order")
        if not job_id:
            return None
        return get_object_or_404(JobOrder, pk=job_id)

    def form_valid2(self, form):
        booking = form.save(commit=False)
        booking.job_order = self.job
        booking.status = VendorBooking.ST_DRAFT
        booking.created_by = self.request.user
        booking.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("shipments:vendor_booking_update", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        job = None
        job_id = self.request.POST.get("job_order") or self.request.GET.get("job_order")
        if job_id:
            job = JobOrder.objects.filter(pk=job_id).first()


        qs = JobCostType.objects.all().order_by("name")

        ctx["cost_types_json"] = list(qs.values("id","code","name","cost_group","service_type"))
        ctx["cost_type_map_json"] = json.dumps(build_cost_type_map(), cls=DjangoJSONEncoder)
        ctx["job_cost_summary"] = build_job_vendor_cost_summary(job) if job else []
        ctx["weight_uoms"] = (
            UOM.objects
               .filter(is_active=True, category__iexact="Weight")
               .order_by("code")
        )
        ctx["is_create"] = True
        prefix = "lines"
        
          # NOTE: pada create GET, self.object biasanya None → formset tetap bisa dibuat tanpa instance
        if self.request.POST:
            ctx["lines_formset"] = VendorBookingLineFormSet(
                self.request.POST,
                instance=getattr(self, "object", None),
                prefix=prefix,
            )
        else:
            ctx["lines_formset"] = VendorBookingLineFormSet(
                instance=getattr(self, "object", None),
                prefix=prefix,
            )

        # optional: kompatibel kalau template masih pakai {{ formset }}
        ctx["formset"] = ctx["lines_formset"]

        
        return ctx
    
class VendorBookingUpdateView(LoginRequiredMixin, UpdateView):
    model = VendorBooking
    form_class = VendorBookingForm
    template_name = "vendor_bookings/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        if self.request.POST:
            ctx["formset"] = VendorBookingLineFormSet(self.request.POST, instance=self.object)
        else:
            ctx["formset"] = VendorBookingLineFormSet(instance=self.object)


        job = None
        job_id = self.request.POST.get("job_order") or self.request.GET.get("job_order")
        if job_id:
            job = JobOrder.objects.filter(pk=job_id).first()


        qs = JobCostType.objects.all().order_by("name")
        ctx["cost_types_json"] = list(qs.values("id","code","name","cost_group","service_type"))
        ctx["cost_type_map_json"] = json.dumps(build_cost_type_map(), cls=DjangoJSONEncoder)
        ctx["weight_uoms"] = (
            UOM.objects
               .filter(is_active=True, category__iexact="Weight")
               .order_by("code")
        )

        ctx["job_cost_summary"] = build_job_vendor_cost_summary(job) if job else []
        # optional: kalau template juga butuh list lines non-formset
        ctx["lines"] = self.object.lines.all().order_by("line_no", "id")
        ctx["taxes"] = Tax.objects.filter(is_active=True).order_by("name") \
            if hasattr(Tax, "is_active") else Tax.objects.all().order_by("name")
        ctx["cost_types"] = JobCostType.objects.filter(is_active=True).order_by("sort_order","name") \
            if hasattr(JobCostType,"is_active") else JobCostType.objects.all().order_by("name")


        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]

        if not formset.is_valid():
            return self.form_invalid(form)

        self.object = form.save()
        formset.instance = self.object
        formset.save()

        # optional: hitung total header
        if hasattr(self.object, "recalc_totals"):
            self.object.recalc_totals()

        return redirect("shipments:vendor_booking_edit", pk=self.object.pk)


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
        b = self.get_object()
        if b.status != VendorBooking.ST_DRAFT:
            return HttpResponseForbidden("Hanya DRAFT yang bisa confirm.")
        if not b.vendor_id:
            return HttpResponseForbidden("Vendor wajib diisi sebelum confirm.")
        b.status = VendorBooking.ST_CONFIRMED
        b.save(update_fields=["status"])
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
