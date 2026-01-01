from django.db import transaction
from sales.models import Invoice, InvoiceLine


def build_invoice_description_from_job(job):
    """
    Description invoice line dari JobOrder:
    - cargo_description
    - pickup → delivery
    """
    parts = []

    cargo = (getattr(job, "cargo_description", "") or "").strip()
    if cargo:
        parts.append(cargo)

    pickup = (
        getattr(job, "pick_up", "")
        or getattr(job, "pickup", "")
        or ""
    ).strip()
    delivery = (getattr(job, "delivery", "") or "").strip()

    route = " → ".join([p for p in [pickup, delivery] if p])
    if route:
        parts.append(route)

    return "\n".join(parts)


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


def recalc_invoice_totals(invoice):
    """
    Hitung ulang subtotal & total invoice dari lines
    (simple & aman)
    """
    total = 0
    price_field = detect_line_price_field()

    lines = (
        invoice.lines.all()
        if hasattr(invoice, "lines")
        else invoice.invoiceline_set.all()
    )

    for line in lines:
        qty = getattr(line, "quantity", 0) or 0
        price = getattr(line, price_field, 0) or 0
        total += qty * price

    if hasattr(invoice, "subtotal_amount"):
        invoice.subtotal_amount = total
    if hasattr(invoice, "total_amount"):
        invoice.total_amount = total

    invoice.save(update_fields=["subtotal_amount", "total_amount"])


def generate_invoice_from_job(job):
    """
    CORE LOGIC:
    - 1 JobOrder = 1 Invoice
    - Invoice dibuat DRAFT
    - 1 Invoice = 1 Line
    """
    if getattr(job, "is_invoiced", False) and job.invoices.exists():
        return job.invoices.order_by("-id").first()

    description = build_invoice_description_from_job(job) or f"Job Order {job.number}"

    with transaction.atomic():
        invoice = Invoice.objects.create(
            job_order=job,
            invoice_date=getattr(job, "job_date", None),
            due_date=getattr(job, "job_date", None),
            status=getattr(Invoice, "STATUS_DRAFT", "DRAFT"),
            subtotal_amount=getattr(job, "total_amount", 0) or 0,
            tax_amount=getattr(job, "tax_amount", 0) or 0,
            total_amount=getattr(job, "grand_total", None) or (
                (getattr(job, "total_amount", 0) or 0)
                + (getattr(job, "tax_amount", 0) or 0)
            ),
            notes_internal=f"Generated from JobOrder {job.number}",
            customer_id=getattr(job, "customer_id", None),
        )

        price_field = detect_line_price_field()

        InvoiceLine.objects.create(
            invoice=invoice,
            description=description,
            quantity=getattr(job, "quantity", None) or 1,
            uom="",      
            **{price_field: getattr(job, "total_amount", 0) or 0},

        )

        if hasattr(job, "is_invoiced"):
            job.is_invoiced = True
            job.save(update_fields=["is_invoiced"])

        recalc_invoice_totals(invoice)

    return invoice
