from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from sales.models import SalesQuotation

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

# sales/actions.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from sales.models import SalesQuotation
from ..models import SalesQuotation, SalesOrder, SalesOrderLine


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



@transaction.atomic
def quotation_generate_po(request, pk):
    q = get_object_or_404(SalesQuotation, pk=pk)

    if q.status != SalesQuotation.STATUS_ACCEPTED:
        messages.error(request, "PO hanya bisa digenerate dari Quotation yang Accepted.")
        return redirect("sales:quotation_detail", pk=q.pk)

    # Cegah duplikasi
    if q.orders.exists():
        so = q.orders.first()
        messages.warning(request, f"PO sudah ada: {so.number}")
        return redirect("sales:quotation_detail", pk=q.pk)

    # Nomor PO sederhana (nanti bisa ganti pakai sequence)
    po_number = f"PO-{q.number}"

    so = SalesOrder.objects.create(
        number=po_number,
        sales_quotation=q,                 # ← FK baru yang benar
        customer=q.customer,
        total_amount=q.total_amount,
        status="DRAFT",
        business_type=q.business_type,
    )

    # Copy lines
    for ln in q.lines.all():
        SalesOrderLine.objects.create(
            sales_order=so,
            origin=ln.origin,
            destination=ln.destination,
            description=ln.description,
            uom=ln.uom,
            qty=ln.qty,
            price=ln.price,
            amount=ln.amount,
        )

    messages.success(request, f"PO {so.number} berhasil dibuat.")
    return redirect("sales:quotation_detail", pk=q.pk)