from datetime import date

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models import F, Sum
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST

from sales.models import SalesQuotation
from ..models import SalesQuotation, SalesOrder, SalesOrderLine
from core.models import NumberSequence
from core.numbering import next_number
from ..auth import sales_access_required, sales_queryset_for_user





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
    Generate SalesOrder dari SalesQuotation.
    - Akses dibatasi via guard (sales_access_required).
    - Ambil quotation via queryset yang sudah difilter per user (sales_queryset_for_user).
    - Cegah double-generate.
    - Isi salesperson = quotation.salesperson (fallback ke request.user).
    - TODO: ganti penomoran next_number sesuai nomorator Anda.
    """
    # Ambil quotation dengan lock, dan sudah difilter object-level per user/role
    q_qs = sales_queryset_for_user(SalesQuotation.objects.select_for_update(), request.user)
    quotation = get_object_or_404(q_qs, pk=pk)

    # Cegah double generate untuk quotation yg sama
    existing = SalesOrder.objects.filter(quotation=quotation).first()
    if existing:
        return redirect(reverse("sales:order_details", args=[existing.pk]))

    # Tentukan salesperson (utama: dari quotation; fallback: request.user)
    salesperson = quotation.salesperson or request.user

    # TODO: ganti ini dengan nomorator final Anda
    next_number = f"SO-{quotation.pk}"

    order = SalesOrder.objects.create(
        quotation=quotation,
        customer=quotation.customer,
        number=next_number,
        salesperson=salesperson,
        status="draft",
    )

    # (Opsional) salin line items dari quotation ke order di sini
    # for ql in quotation.lines.all():
    #     OrderLine.objects.create(
    #         order=order,
    #         description=ql.description,
    #         quantity=ql.quantity,
    #         price=ql.price,
    #         ...
    #     )

    return redirect(reverse("sales:order_details", args=[order.pk]))


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
