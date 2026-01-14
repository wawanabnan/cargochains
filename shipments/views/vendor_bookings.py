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

# views.py
import json
from django.core.serializers.json import DjangoJSONEncoder

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
        self.job = get_object_or_404(JobOrder, pk=self.kwargs["job_id"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
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
        ctx["job"] = self.job
        ctx["cost_type_map_json"] = json.dumps(build_cost_type_map(), cls=DjangoJSONEncoder)
        ctx["is_create"] = True
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

        qs = JobCostType.objects.all().order_by("name")
        ctx["cost_types_json"] = list(qs.values("id","code","name","cost_group","service_type"))
        ctx["cost_type_map_json"] = json.dumps(build_cost_type_map(), cls=DjangoJSONEncoder)

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
