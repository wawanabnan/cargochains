from decimal import Decimal
from django.db import transaction
from billing.models.customer_invoice import Invoice, InvoiceLine
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP



def _dec(value):
    return Decimal(str(value or 0))

def recalc_invoice_totals(invoice):
    """
    Final rule:
    - subtotal = sum(line.quantity × line.price)
    - tax_amount = sum(line tax per rate)
    - total_amount = subtotal + tax_amount
    """

    lines_qs = (
        invoice.lines.all()
        if hasattr(invoice, "lines")
        else invoice.invoiceline_set.all()
    ).prefetch_related("taxes")

    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")

    for line in lines_qs:
        qty = _dec(line.quantity)
        price = _dec(line.price)

        base = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal += base

        for tax in line.taxes.all():
            rate = _dec(getattr(tax, "rate", 0))
            tax_total += (base * rate / Decimal("100")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

    invoice.subtotal_amount = subtotal
    invoice.tax_amount = tax_total
    invoice.total_amount = subtotal + tax_total

    invoice.save(update_fields=[
        "subtotal_amount",
        "tax_amount",
        "total_amount"
    ])

    return invoice

def detect_line_price_field():
    """
    Deteksi nama field price di InvoiceLine
    (price / unit_price / rate / unit_rate)
    """
    for name in ("price", "unit_price", "rate", "unit_rate"):
        try:
            InvoiceLine._meta.get_field(name)
            return name
        except Exception:
            pass
    return "price"

def build_invoice_description(job, invoice_type):
    """
    Description hanya operasional.
    Tidak ada format uang.
    Tidak ada summary angka.
    """

    lines = []

    if invoice_type == Invoice.INV_DP:
        lines.append(f"Down Payment {job.down_payment_percent}% - {job.number}")
    else:
        lines.append(f"Final Invoice - {job.number}")

    # Service
    if job.service and getattr(job.service, "name", None):
        lines.append(job.service.name)

    # Route
    origin = getattr(job, "pick_up", None) or getattr(job, "pickup", None)
    destination = getattr(job, "delivery", None)

    route_parts = [p for p in [origin, destination] if p]
    if route_parts:
        lines.append(" → ".join(route_parts))

    # Cargo
    cargo = getattr(job, "cargo_description", None)
    if cargo:
        lines.append(cargo)

    return "\n".join(lines)


def generate_invoice_from_job(job, invoice_type, user):
    """
    Generate DRAFT invoice from Job Order.
    Supports:
    - DP
    - FINAL
    """

    if invoice_type not in {Invoice.INV_DP, Invoice.INV_FINAL}:
        raise ValidationError("Invalid invoice type.")

    # =============================
    # DETERMINE BASE AMOUNT
    # =============================
    if invoice_type == Invoice.INV_DP:

        if not job.can_generate_dp:
            raise ValidationError("DP invoice cannot be generated.")

        base_amount = job.down_payment_amount

    else:  # FINAL

        if not job.can_generate_final:
            raise ValidationError("Final invoice cannot be generated.")

        base_amount = job.remaining_invoiceable

    if base_amount <= 0:
        raise ValidationError("Invoice amount is zero.")

    description = build_invoice_description(job, invoice_type)

    # =============================
    # CREATE INVOICE
    # =============================
    with transaction.atomic():
        if invoice_type == Invoice.INV_DP:
            if Invoice.objects.select_for_update().filter(
                job_order=job,
                invoice_type=Invoice.INV_DP
            ).exists():
                raise ValidationError("DP invoice already exists.")


        invoice = Invoice.objects.create(
            job_order=job,
            invoice_type=invoice_type,
            customer=job.customer,
            currency=job.currency,
            payment_term=job.payment_term,
            subtotal_amount=0,
            tax_amount=0,
            total_amount=0,
            tax_locked=True,  
            status=Invoice.ST_DRAFT,
            created_by=user,
        )

        line = InvoiceLine.objects.create(
            invoice=invoice,
            description=description,
            quantity=1,
            price=base_amount,
            amount=base_amount,
            service=job.service if hasattr(job, "service") else None,
        )

        # Copy taxes from service
        if job.service and hasattr(job.service, "taxes"):
            line.taxes.set(job.service.taxes.all())

        # Calculate totals
        recalc_invoice_totals(invoice)

    return invoice