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




@transaction.atomic
def quotation_generate_so(request, pk):
    # Ambil quotation
    q = get_object_or_404(SalesQuotation, pk=pk)

    # Hanya boleh generate dari ACCEPTED
    if q.status != SalesQuotation.STATUS_ACCEPTED:
        messages.error(request, "Generate Order hanya bisa dari Quotation berstatus ACCEPTED.")
        return redirect("sales:quotation_detail", pk=q.pk)

    # Pastikan ada currency (sering NOT NULL di SO)
    if not getattr(q, "currency_id", None):
        messages.error(request, "Quotation belum memiliki currency. Lengkapi dulu currency-nya.")
        return redirect("sales:quotation_detail", pk=q.pk)



    from core.utils import get_next_number
    SEQ_CODE_ORDER_BY_TYPE = {
        "freight": "FREIGHT_ORDER",   # konsisten dengan data di DB
        "charter": "CHARTER_ORDER",
    }

    bt = (q.business_type or "freight").lower()
    seq_code = SEQ_CODE_ORDER_BY_TYPE.get(bt, "FREIGHT_ORDER")
   
    so_number = get_next_number("sales", seq_code)
    so = SalesOrder.objects.create(
        number=so_number,
        sales_quotation=q,
        customer=q.customer,
        status=SalesOrder.STATUS_DRAFT,
        business_type=q.business_type,
        currency=q.currency,
        payment_term=getattr(q, "payment_term", None),
        sales_service=getattr(q, "sales_service", None),
        sales_user=getattr(q, "sales_user", None),
        sales_agency=getattr(q, "sales_agency", None),
        total=getattr(q, "total", 0),
        vat=getattr(q, "vat", 0),
        grand_total=getattr(q, "grand_total", 0),
    )


    # Copy lines dari quotation ke order
    q_lines = q.lines.all()
    bulk = []
    for ln in q_lines:
        bulk.append(SalesOrderLine(
            sales_order=so,
            origin=ln.origin,
            destination=ln.destination,
            description=ln.description,
            qty=ln.qty,
            uom=ln.uom,
            price=ln.price,
            amount=getattr(ln, "amount", None) or (ln.qty * ln.price),
        ))
    if bulk:
        SalesOrderLine.objects.bulk_create(bulk)

    # (Opsional) Re-calc total dari lines bila total kosong
    if not so.total or not so.grand_total:
        agg = so.lines.annotate(line_total=F("qty") * F("price")).aggregate(s=Sum("line_total"))
        subtotal = agg["s"] or 0
        vat = so.vat or 0
        so.total = subtotal
        so.grand_total = subtotal + vat
        so.save(update_fields=["total", "grand_total"])

    # Update status quotation → ORDERED (final)
    if q.can_transition_to(SalesQuotation.STATUS_ORDERED):
        q.status = SalesQuotation.STATUS_ORDERED
        q.save(update_fields=["status"])

    messages.success(request, f"Sales Order {so.number} berhasil dibuat.")
    return redirect("sales:order_details", pk=so.pk)  # atau ke quotation_detail, terserah kamu


# sales/views/so_to_shipment.py
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction

from sales import models as sm
from shipments.services.generators import create_shipment_from_sales_order


@login_required
@transaction.atomic
def order_generate_shipment(request, pk):
    so = get_object_or_404(sm.SalesOrder, pk=pk)
    shp = create_shipment_from_sales_order(so, user=request.user)
    messages.success(request, f"Shipment {shp.number} dibuat dari SO {so.number}.")
    # sesuaikan nama url detail shipment
    return redirect("shipments:shipment_details", pk=shp.pk)
