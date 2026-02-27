from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from decimal import Decimal

from billing.models.customer_invoice import Invoice,InvoiceLine  # sesuaikan path


@require_GET
@login_required
def invoice_customer_receipt_info(request):
    inv_id = request.GET.get("invoice_id")
    if not inv_id:
        return JsonResponse({"error": "missing invoice_id"}, status=400)

    inv = (
        Invoice.objects
        .select_related("customer")
        .filter(pk=inv_id)
        .first()
    )
    if not inv:
        return JsonResponse({"error": "invoice not found"}, status=404)

    outstanding = inv.outstanding_amount  # property yg kita sudah sepakat

    return JsonResponse({
        "invoice_id": inv.id,
        "invoice_number": inv.number,
        "customer_id": inv.customer_id,
        "customer_name": str(inv.customer),
        "outstanding": str(outstanding or Decimal("0.00")),
        "apply_pph": bool(getattr(inv, "apply_pph", False)),
        "pph_amount": str(getattr(inv, "pph_amount", Decimal("0.00")) or Decimal("0.00")),
    })
