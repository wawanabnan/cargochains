# shipments/views/vendor_bookings.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, CreateView, UpdateView

from shipments.models.vendor_bookings import VendorBooking
from shipments.forms.vendor_bookings import VendorBookingForm, VendorBookingLineFormSet
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView


def _st(model, name, fallback: str):
    """ambil konstanta status dari model kalau ada, fallback ke string."""
    return getattr(model, name, fallback)


ST_DRAFT = _st(VendorBooking, "ST_DRAFT", "draft")
ST_SENT = _st(VendorBooking, "ST_SENT", "sent")
ST_CONFIRMED = _st(VendorBooking, "ST_CONFIRMED", "confirmed")
ST_COMPLETED = _st(VendorBooking, "ST_COMPLETED", "completed")
ST_CANCELLED = _st(VendorBooking, "ST_CANCELLED", "cancelled")


def _booking_min_ready(booking: VendorBooking):
    """
    Gate minimal sebelum naik status:
    - vendor ada
    - currency ada
    - punya minimal 1 line (non-deleted)
    - kalau job_order null => hanya boleh draft (jadi saat Send/Confirm wajib ada job_order)
    """
    missing = []
    if not booking.vendor_id:
        missing.append("Vendor belum diisi.")
    if not getattr(booking, "currency_id", None):
        missing.append("Currency belum diisi.")
    # lines: minimal 1 aktif
    line_qs = booking.lines.all() if hasattr(booking, "lines") else booking.vendorbookingline_set.all()
    if not line_qs.exists():
        missing.append("Booking line masih kosong.")
    if booking.job_order_id is None:
        missing.append("Job Order wajib diisi untuk status selain Draft.")
    return missing


def _recalc_total(booking: VendorBooking) -> None:
    """Server-side total: sum(qty * unit_price) lines yang tidak dihapus."""
    line_qs = booking.lines.all() if hasattr(booking, "lines") else booking.vendorbookingline_set.all()
    total = 0
    for ln in line_qs:
        qty = float(getattr(ln, "qty", 0) or 0)
        unit_price = float(getattr(ln, "unit_price", 0) or 0)
        total += qty * unit_price
    booking.total_amount = total



class VendorBookingListView(LoginRequiredMixin, ListView):
    model = VendorBooking
    template_name = "vendor_booking/list.html"
    context_object_name = "rows"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            VendorBooking.objects
            .select_related("job_order", "vendor", "currency")
            .order_by("-booking_date", "-id")
        )

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(number__icontains=q)

        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)

        unlinked = (self.request.GET.get("unlinked") or "").strip()
        if unlinked == "1":
            qs = qs.filter(job_order__isnull=True)

        return qs


class VendorBookingDetailView(LoginRequiredMixin, DetailView):
    model = VendorBooking
    template_name = "vendor_booking/detail.html"
    context_object_name = "booking"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        booking = ctx["booking"]
        line_qs = booking.lines.all() if hasattr(booking, "lines") else booking.vendorbookingline_set.all()
        ctx["lines"] = line_qs
        ctx["can_send"] = booking.status == ST_DRAFT
        ctx["can_confirm"] = booking.status == ST_SENT
        ctx["can_complete"] = booking.status == ST_CONFIRMED
        ctx["can_cancel"] = booking.status in (ST_DRAFT, ST_SENT, ST_CONFIRMED)
        ctx["locked"] = booking.status in (ST_CONFIRMED, ST_COMPLETED, ST_CANCELLED)
        return ctx


class VendorBookingCreateView(LoginRequiredMixin, CreateView):
    model = VendorBooking
    form_class = VendorBookingForm
    template_name = "vendor_booking/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["formset"] = VendorBookingLineFormSet(self.request.POST or None)
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]

        if not formset.is_valid():
            return self.form_invalid(form)

        obj = form.save()
        formset.instance = obj
        formset.save()

        _recalc_total(obj)
        obj.save(update_fields=["total_amount"])

        messages.success(self.request, "Vendor Booking dibuat.")
        return redirect("shipments:vendor_booking_detail", pk=obj.pk)


class VendorBookingUpdateView(LoginRequiredMixin, UpdateView):
    model = VendorBooking
    form_class = VendorBookingForm
    template_name = "vendor_booking/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        booking = self.object

        if self.request.POST:
            ctx["formset"] = VendorBookingLineFormSet(self.request.POST, instance=booking)
        else:
            ctx["formset"] = VendorBookingLineFormSet(instance=booking)

        locked = booking.status in (ST_CONFIRMED, ST_COMPLETED, ST_CANCELLED)
        if locked:
            # lock header kecuali notes (opsional)
            for name, f in ctx["form"].fields.items():
                if name in ("pickup_note", "delivery_note", "remarks"):
                    continue
                f.disabled = True
            for lf in ctx["formset"].forms:
                for name, f in lf.fields.items():
                    f.disabled = True
                if "DELETE" in lf.fields:
                    lf.fields["DELETE"].disabled = True

        ctx["locked"] = locked
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]

        if not formset.is_valid():
            return self.form_invalid(form)

        obj = form.save()
        formset.save()

        _recalc_total(obj)
        obj.save(update_fields=["total_amount"])

        messages.success(self.request, "Vendor Booking tersimpan.")
        return redirect("shipments:vendor_booking_detail", pk=obj.pk)


# ===== ACTIONS (POST ONLY) =====

class _BookingActionBase(LoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(VendorBooking, pk=pk)
        return self.handle(request, booking)

    def handle(self, request, booking: VendorBooking):
        raise NotImplementedError


class VendorBookingSendView(_BookingActionBase):
    @transaction.atomic
    def handle(self, request, booking):
        if booking.status != ST_DRAFT:
            messages.error(request, "Hanya bisa Send dari status Draft.")
            return redirect("shipments:vendor_booking_detail", pk=booking.pk)

        missing = _booking_min_ready(booking)
        if missing:
            messages.error(request, "Tidak bisa Send:\n- " + "\n- ".join(missing))
            return redirect("shipments:vendor_booking_detail", pk=booking.pk)

        _recalc_total(booking)
        booking.status = ST_SENT
        booking.save(update_fields=["status", "total_amount"])
        messages.success(request, "Booking dikirim (Sent).")
        return redirect("shipments:vendor_booking_detail", pk=booking.pk)


class VendorBookingConfirmView(_BookingActionBase):
    @transaction.atomic
    def handle(self, request, booking):
        if booking.status != ST_SENT:
            messages.error(request, "Hanya bisa Confirm dari status Sent.")
            return redirect("shipments:vendor_booking_detail", pk=booking.pk)

        missing = _booking_min_ready(booking)
        if missing:
            messages.error(request, "Tidak bisa Confirm:\n- " + "\n- ".join(missing))
            return redirect("shipments:vendor_booking_detail", pk=booking.pk)

        _recalc_total(booking)
        booking.status = ST_CONFIRMED
        booking.save(update_fields=["status", "total_amount"])
        messages.success(request, "Booking berhasil Confirmed.")
        return redirect("shipments:vendor_booking_detail", pk=booking.pk)


class VendorBookingCompleteView(_BookingActionBase):
    @transaction.atomic
    def handle(self, request, booking):
        if booking.status != ST_CONFIRMED:
            messages.error(request, "Hanya bisa Complete dari status Confirmed.")
            return redirect("shipments:vendor_booking_detail", pk=booking.pk)

        booking.status = ST_COMPLETED
        booking.save(update_fields=["status"])
        messages.success(request, "Booking Completed.")
        return redirect("shipments:vendor_booking_detail", pk=booking.pk)


class VendorBookingCancelView(_BookingActionBase):
    @transaction.atomic
    def handle(self, request, booking):
        if booking.status not in (ST_DRAFT, ST_SENT, ST_CONFIRMED):
            messages.error(request, "Tidak bisa Cancel dari status saat ini.")
            return redirect("shipments:vendor_booking_detail", pk=booking.pk)

        booking.status = ST_CANCELLED
        booking.save(update_fields=["status"])
        messages.success(request, "Booking Cancelled.")
        return redirect("shipments:vendor_booking_detail", pk=booking.pk)
