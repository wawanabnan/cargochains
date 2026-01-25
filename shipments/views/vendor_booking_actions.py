from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from job.models.job_orders import JobOrder
from shipments.services.vendor_booking_services import generate_vendor_bookings_from_job
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseNotAllowed
from shipments.models.vendor_bookings import VendorBooking
from shipments.services.vendor_booking_totals import recompute_vendor_booking_totals
from decimal import Decimal
from django.core.exceptions import ValidationError
from shipments.utils.flash import flash_errors





IDR_CURRENCY_ID = 1  # kalau IDR pk=1 (sesuaikan bila beda)

def _d(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    try:
        return Decimal(v)
    except Exception:
        return Decimal("0")


@login_required
@require_POST
def generate_vendor_booking(request, pk):
    job = get_object_or_404(JobOrder, pk=pk)

    bookings = generate_vendor_bookings_from_job(job, user=request.user)

    if bookings:
        messages.success(request, f"✅ Generated {len(bookings)} Vendor Booking (DRAFT).")
    else:
        messages.info(request, "ℹ️ Tidak ada cost line vendor yang perlu digenerate (atau sudah pernah digenerate).")

    return redirect("job:job_order_details", pk=job.pk)


from decimal import Decimal
from django.utils import timezone
from django.contrib import messages

from shipments.services.vendor_booking_totals import recompute_vendor_booking_totals
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

IDR_CURRENCY_ID = 1  # sesuaikan kalau bukan 1


def _d(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    try:
        return Decimal(v)
    except Exception:
        return Decimal("0")

class VendorBookingActionView(LoginRequiredMixin, View):
    allowed_from = []
    next_status = None
    success_message = ""
    update_fields = []

    def before_transition(self, request, vb):
        return None

    def apply_audit(self, request, vb):
        return None

    def after_transition(self, request, vb):
        return None
    
    def post(self, request, pk):
        vb = get_object_or_404(VendorBooking, pk=pk)

        if vb.status not in self.allowed_from:
            messages.warning(request, "Aksi tidak diizinkan dari status ini.")
            return redirect("shipments:vendor_booking_update", pk=vb.pk)

        try:
            resp = self.before_transition(request, vb)
            if resp is not None:
                return resp

            vb.status = self.next_status

            resp = self.apply_audit(request, vb)
            if resp is not None:
                return resp

            vb.save(update_fields=["status"] + list(self.update_fields))

            resp = self.after_transition(request, vb)
            if resp is not None:
                return resp

        except ValidationError as e:
              return redirect("shipments:vendor_booking_update", pk=vb.pk)


        if self.success_message:
            messages.success(request, self.success_message)

        return redirect("shipments:vendor_booking_update", pk=vb.pk)


class VendorBookingSubmitView(VendorBookingActionView):
    allowed_from = [VendorBooking.ST_DRAFT]
    next_status = VendorBooking.ST_SUBMITTED
    success_message = "Submitted ✅"
    update_fields = ["submitted_at", "submitted_by"]

    def before_transition(self, request, vb):
        errors = []


        if request.user.is_authenticated:
            vb.submitted_by = request.user
        else:
            vb.submitted_by = None

        # header
        if not vb.vendor_id:
            errors.append("Vendor wajib diisi.")
        if not vb.currency_id:
            errors.append("Currency wajib diisi.")
        if not getattr(vb, "booking_date", None):
            errors.append("Booking date wajib diisi.")

        if vb.currency_id and int(vb.currency_id) != int(IDR_CURRENCY_ID):
            rate = _d(getattr(vb, "idr_rate", None))
            if rate <= 0:
                errors.append("IDR rate wajib > 0 untuk currency non-IDR.")

        # lines
        qs = vb.lines.all()
        if not qs.exists():
            errors.append("Minimal 1 line wajib ada.")
        else:
            for idx, ln in enumerate(qs.order_by("id"), start=1):
                desc = (getattr(ln, "description", "") or "").strip()
                if not desc:
                    errors.append(f"Line #{idx}: Description wajib diisi.")

                qty = _d(getattr(ln, "qty", None))
                if qty <= 0:
                    errors.append(f"Line #{idx}: Qty wajib > 0.")

                if not getattr(ln, "uom_id", None):
                    errors.append(f"Line #{idx}: UOM wajib ada.")

                unit_price = _d(getattr(ln, "unit_price", None))
                if unit_price < 0:
                    errors.append(f"Line #{idx}: Unit price tidak boleh negatif.")

        
        if errors:
            flash_errors(request, errors, title="Submit gagal", max_items=3)
            return redirect("shipments:vendor_booking_update", pk=vb.pk)


        # totals must be consistent for approver
        recompute_vendor_booking_totals(vb, recompute_lines=True)
        return None

    def apply_audit(self, request, vb):
        vb.submitted_at = timezone.now()
        vb.submitted_by = request.user
        return None




class VendorBookingApproveView(VendorBookingActionView):
    allowed_from = [VendorBooking.ST_SUBMITTED]
    next_status = VendorBooking.ST_APPROVED
    success_message = "Approved"
    update_fields = ["approved_at", "approved_by"]

    def apply_audit(self, request, vb):
        vb.approved_at = timezone.now()
        vb.approved_by = request.user


class VendorBookingRejectView(VendorBookingActionView):
    allowed_from = [VendorBooking.ST_SUBMITTED]
    next_status = VendorBooking.ST_DRAFT
    success_message = "Rejected back to Draft"


from shipments.models.shipping_instruction import ShippingInstructionDocument
from shipments.services.vendor_booking_totals import recompute_vendor_booking_totals
from django.db import transaction
from core.utils.numbering import get_next_number


class VendorBookingConfirmView(VendorBookingActionView):
    allowed_from = [VendorBooking.ST_APPROVED]
    next_status = VendorBooking.ST_CONFIRMED
    success_message = "Vendor Booking confirmed"

    def after_transition(self, request, vb):
        # nanti di sini generate ShippingInstructionDocument kalau SEA
        pass

    def before_transition(self, request, vb):
        # optional: recompute totals sekali lagi sebelum lock
        recompute_vendor_booking_totals(vb, recompute_lines=True)
        return None

    @transaction.atomic
    def post(self, request, pk):
        # override post supaya atomic bener-bener cover status+doc
        return super().post(request, pk)

    def after_transition(self, request, vb):
        group = get_vb_group(vb)

        if group != "SEA":
            return None  # non-sea: tidak bikin SI

        # ✅ Idempotent: kalau sudah pernah dibuat, jangan bikin lagi
        doc = getattr(vb, "shipping_instruction", None)
        if doc:
            messages.info(request, "Shipping Instruction sudah ada.")
            return redirect("shipments:shipping_instruction_update", pk=doc.pk)

        # create doc
        doc = ShippingInstructionDocument.objects.create(
            vendor_booking=vb,
            job_order_id=vb.job_order_id,
            issued_date=timezone.localdate(),
            issued_by=request.user,
            si_number=get_next_number("shipments", "SHIPPING_INSTRUCTION"),
        )

        # ✅ setelah confirm SEA, langsung lempar ke menu SI
        return redirect("shipments:shipping_instruction_update", pk=doc.pk)



class VendorBookingSendView(VendorBookingActionView):
    allowed_from = [VendorBooking.ST_CONFIRMED]
    next_status = VendorBooking.ST_SENT
    success_message = "Sent to vendor"
    update_fields = ["sent_at", "sent_by"]

    def apply_audit(self, request, vb):
        vb.sent_at = timezone.now()
        vb.sent_by = request.user

class VendorBookingCloseView(VendorBookingActionView):
    allowed_from = [VendorBooking.ST_SENT, VendorBooking.ST_CONFIRMED]
    next_status = VendorBooking.ST_CLOSED
    success_message = "Vendor Booking closed"
    update_fields = ["closed_at", "closed_by"]

    def apply_audit(self, request, vb):
        vb.closed_at = timezone.now()
        vb.closed_by = request.user

class VendorBookingCancelView(VendorBookingActionView):
    allowed_from = [
        VendorBooking.ST_DRAFT,
        VendorBooking.ST_SUBMITTED,
        VendorBooking.ST_APPROVED,
        VendorBooking.ST_CONFIRMED,
        VendorBooking.ST_SENT,
    ]
    next_status = VendorBooking.ST_CANCELLED
    success_message = "Vendor Booking cancelled"
    update_fields = ["cancelled_at", "cancelled_by"]

    def apply_audit(self, request, vb):
        vb.cancelled_at = timezone.now()
        vb.cancelled_by = request.user
