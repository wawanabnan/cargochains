from datetime import date

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models import F, Sum
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST

from sales.models import SalesQuotation,SalesQuotationLine
from ..models import SalesQuotation, SalesOrder, SalesOrderLine
from core.models import NumberSequence
from core.numbering import next_number
from ..auth import sales_access_required, sales_queryset_for_user
from django.urls import reverse
from django.db import transaction, IntegrityError
from decimal import Decimal




ALLOWED_DELETE_STATUSES = {"draft", "cancelled"}

def quotation_delete(request, pk):
    """
    Action delete quotation.
    Hanya boleh untuk status draft/cancelled.
    """
    q = get_object_or_404(SalesQuotation, pk=pk)
    if q.status not in ALLOWED_DELETE_STATUSES:
        messages.warning(request, f"Cannot delete {q.number} (status={q.status})")
        return redirect("sales:freight_quotation_detail", pk=pk)

    q.delete()
    messages.success(request, f"Deleted quotation {q.number}")
    return redirect("sales:freight_quotation_list")



#@login_required
@require_POST
def quotation_change_status(request, pk):
    quotation = get_object_or_404(SalesQuotation, pk=pk)
    new_status = (request.POST.get("status") or "").upper().strip()

    messages.debug(request, f"[DEBUG] posted status='{new_status}', current='{quotation.status}'")

    valid_statuses = {
        SalesQuotation.STATUS_SENT,
        SalesQuotation.STATUS_ACCEPTED,
        SalesQuotation.STATUS_CANCELLED,
    }

    if new_status not in valid_statuses:
        messages.error(request, "Status tidak dikenal.")
        return redirect("sales:quotation_detail", pk=quotation.pk)

    # Khusus EXPIRED: hanya dari SENT dan setelah valid_until lewat
    if new_status == SalesQuotation.STATUS_EXPIRED:
        if quotation.status != SalesQuotation.STATUS_SENT:
            messages.error(request, "Hanya penawaran berstatus SENT yang bisa ditandai EXPIRED.")
            return redirect("sales:quotation_detail", pk=quotation.pk)
        if quotation.valid_until:
            today = timezone.localdate()
            if today <= quotation.valid_until:
                messages.error(request, "Belum melewati tanggal valid_until, tidak bisa EXPIRED.")
                return redirect("sales:quotation_detail", pk=quotation.pk)

    # Cek aturan transisi umum
    if not quotation.can_transition_to(new_status):
        messages.error(request, f"Tidak bisa mengubah status dari {quotation.status} ke {new_status}.")
        return redirect("sales:quotation_detail", pk=quotation.pk)

    with transaction.atomic():
        old = quotation.status
        quotation.status = new_status
        quotation.save(update_fields=["status"])
        messages.success(request, f"Status berubah: {old} → {new_status}.")

    return redirect("sales:quotation_detail", pk=quotation.pk)

def _has_field(model, name):
    try:
        model._meta.get_field(name); return True
    except Exception:
        return False




@require_POST
def order_change_status(request, pk):
    so = get_object_or_404(SalesOrder, pk=pk)
    new_status = (request.POST.get("status") or "").upper().strip()
    if not so.can_transition_to(new_status):
        messages.error(request, f"Transisi tidak valid: {so.status} → {new_status}")
        return redirect("sales:order_detail", pk=so.pk)
    old = so.status
    so.status = new_status
    so.save(update_fields=["status"])
    messages.success(request, f"Status Order {so.number} berubah: {old} → {new_status}")
    return redirect("sales:order_detail", pk=so.pk)




#---generate so
@require_POST
@sales_access_required
@transaction.atomic
def quotation_generate_so(request, pk):
    """
    Generate SalesOrder dari SalesQuotation (idempotent + copy lines).
    - Login sudah ditangani via login_required di urls.py.
    - Cek currency & field wajib lain agar tidak IntegrityError.
    """

    # 1) Ambil quotation (lock row) + filter object-level per user
    q_qs = sales_queryset_for_user(
        SalesQuotation.objects.select_for_update(),
        request.user
    )
    quotation = get_object_or_404(q_qs, pk=pk)

    # 2) Idempotent: jika SO sudah ada → redirect
    existing = SalesOrder.objects.filter(sales_quotation=quotation).first()
    if existing:
        messages.info(request, "Sales Order sudah ada untuk quotation ini.")
        return redirect(reverse("sales:order_details", args=[existing.pk]))

    # 3) Validasi workflow (opsional, sesuaikan)
    if getattr(quotation, "status", None) not in ("ACCEPTED", "ORDERED"):
        messages.error(request, "Quotation harus ACCEPTED sebelum generate SO.")
        return redirect(reverse("sales:quotation_detail", args=[quotation.pk]))

    # 4) Validasi data wajib agar tidak IntegrityError
    missing = []
    if not getattr(quotation, "customer_id", None):
        missing.append("Customer")
    if not getattr(quotation, "currency_id", None):
        missing.append("Currency")
    # tambahkan jika payment_term/sales_agency/sales_service wajib di DB-mu:
    # if not getattr(quotation, "payment_term_id", None): missing.append("Payment Term")
    # if not getattr(quotation, "sales_agency_id", None): missing.append("Sales Agency")
    # if not getattr(quotation, "sales_service_id", None): missing.append("Sales Service")
    if missing:
        messages.error(
            request,
            f"Field wajib belum lengkap di Quotation: {', '.join(missing)}."
        )
        return redirect(reverse("sales:quotation_detail", args=[quotation.pk]))

    # 5) Tentukan sales_user (fallback ke user login)
    sales_user = getattr(quotation, "sales_user", None) or request.user

    # 6) Nomor order (sementara). Nanti ganti ke core.NumberSequence.
    next_number = f"SO-{quotation.pk}"

    try:
        # 7) Buat SalesOrder (header)
        order = SalesOrder.objects.create(
            sales_quotation=quotation,
            sales_user=sales_user,

            customer=quotation.customer,
            currency=quotation.currency,
            payment_term=getattr(quotation, "payment_term", None),
            sales_agency=getattr(quotation, "sales_agency", None),
            sales_service=getattr(quotation, "sales_service", None),

            number=next_number,
            status="draft",
            date=getattr(quotation, "date", None) or timezone.now().date(),

            total=getattr(quotation, "total", 0) or Decimal("0"),
            vat=getattr(quotation, "vat", 0) or Decimal("0"),
            grand_total=getattr(quotation, "grand_total", 0) or Decimal("0"),

            business_type=getattr(quotation, "business_type", None),
            notes=getattr(quotation, "notes", "") or "",
        )

        # 8) Copy semua line dari quotation → order (bulk_create)
        q_lines = (
            SalesQuotationLine.objects
            .filter(sales_quotation=quotation)
            .select_related("origin", "destination", "uom")
        )

        order_lines = []
        for ql in q_lines:
            qty = ql.qty or Decimal("0")
            price = ql.price or Decimal("0")
            amount = ql.amount if ql.amount is not None else qty * price

            order_lines.append(
                SalesOrderLine(
                    sales_order=order,
                    origin=ql.origin,
                    destination=ql.destination,
                    description=ql.description,
                    uom=ql.uom,
                    qty=qty,
                    price=price,
                    amount=amount or Decimal("0"),
                )
            )

        if order_lines:
            SalesOrderLine.objects.bulk_create(order_lines, batch_size=500)

            # 9) Recalculate total dari lines (lebih akurat kalau quotation.total kosong)
            recalculated_total = sum(
                (ol.amount or Decimal("0")) for ol in order.lines.all()
            )
            # Jika VAT mengikuti quotation, pakai nilai yg sudah ada; kalau mau auto 11% contoh:
            # vat = (recalculated_total * Decimal("0.11")).quantize(Decimal("0.01"))
            vat = order.vat or Decimal("0")
            order.total = recalculated_total
            order.grand_total = recalculated_total + vat
            order.save(update_fields=["total", "grand_total"])

        # 10) (Opsional) Update status quotation → ORDERED
        if getattr(quotation, "status", None) == "ACCEPTED":
            quotation.status = "ORDERED"
            quotation.save(update_fields=["status"])

        messages.success(request, f"Sales Order {order.number} berhasil dibuat.")
        return redirect(reverse("sales:order_details", args=[order.pk]))

    except IntegrityError as e:
        messages.error(request, f"Gagal membuat Sales Order (integrity error).")
        return redirect(reverse("sales:quotation_detail", args=[quotation.pk]))
    except Exception as e:
        messages.error(request, f"Terjadi error: {e}")
        return redirect(reverse("sales:quotation_detail", args=[quotation.pk]))


# sales/views/actions.py

@login_required
@require_POST
@transaction.atomic

def order_set_status(request, pk):
    so = get_object_or_404(
        sales_queryset_for_user(SalesOrder.objects.all(), request.user, include_null=True),
        pk=pk
    )
    to = (request.POST.get("to") or "").strip().lower()
    cur = (so.status or "draft").strip().lower()

    allowed = {
        "draft": {"confirmed", "canceled"},
        "open": {"confirmed", "canceled"},
        "confirmed": {"processed", "canceled"},
        "processed": {"done", "canceled"},
        "in progress": {"done", "canceled"},
        "done": set(),
        "completed": set(),
        "canceled": set(),
        "cancelled": set(),
    }

    if to not in allowed.get(cur, set()):
        messages.error(request, f"Transisi status {cur} → {to} tidak diizinkan.")
        return redirect(request.POST.get("next") or "sales:order_list")

    so.status = to
    so.save(update_fields=["status"])
    messages.success(request, f"Order {so.number} diubah ke '{to}'.")
    return redirect(request.POST.get("next") or "sales:order_list")


# sales/views/actions.py
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from ..models import SalesOrder
from ..auth import sales_queryset_for_user

@login_required
@require_POST
@transaction.atomic
def order_set_status(request, pk):
    so = get_object_or_404(
        sales_queryset_for_user(SalesOrder.objects.all(), request.user, include_null=True),
        pk=pk
    )
    to = (request.POST.get("to") or "").strip().lower()
    cur = (so.status or "draft").strip().lower()

    allowed = {
        "draft": {"confirmed", "canceled"},
        "open": {"confirmed", "canceled"},
        "confirmed": {"processed", "canceled"},
        "processed": {"done", "canceled"},
        "in progress": {"done", "canceled"},
        "done": set(), "completed": set(),
        "canceled": set(), "cancelled": set(),
    }

    if to not in allowed.get(cur, set()):
        messages.error(request, f"Transisi status {cur} → {to} tidak diizinkan.")
    else:
        so.status = to
        so.save(update_fields=["status"])
        messages.success(request, f"Order {so.number} diubah ke '{to}'.")

    return redirect(request.POST.get("next") or "sales:order_list")
