from decimal import Decimal
from django.db import transaction
from sales.models import Invoice, InvoiceLine
from django.core.exceptions import ValidationError


def _dec(v):
    return Decimal(str(v or 0))


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


def recalc_invoice_totals2(invoice):
    """
    Hitung ulang subtotal & total invoice dari lines
    subtotal = sum(qty * price)
    total    = subtotal + tax_amount (kalau ada)
    """
    subtotal = 0
    price_field = detect_line_price_field()

    lines = (
        invoice.lines.all()
        if hasattr(invoice, "lines")
        else invoice.invoiceline_set.all()
    )

    for line in lines:
        qty = getattr(line, "quantity", 0) or 0
        price = getattr(line, price_field, 0) or 0
        subtotal += qty * price

    if hasattr(invoice, "subtotal_amount"):
        invoice.subtotal_amount = subtotal

    tax = getattr(invoice, "tax_amount", 0) or 0
    if hasattr(invoice, "total_amount"):
        invoice.total_amount = subtotal + tax

    invoice.save(update_fields=["subtotal_amount", "total_amount"])



def recalc_invoice_totals(invoice):
    """
    FINAL RULE (legacy header tax deprecated):
    - subtotal = sum(base line)
    - tax_amount = sum(tax per line from line.taxes)
    - total = subtotal + tax_amount
    """
    price_field = detect_line_price_field()

    # support either related_name="lines" or default invoiceline_set
    lines_qs = invoice.lines.all() if hasattr(invoice, "lines") else invoice.invoiceline_set.all()
    # prefetch taxes to avoid N+1
    try:
        lines_qs = lines_qs.prefetch_related("taxes")
    except Exception:
        pass

    subtotal = Decimal("0")
    tax_total = Decimal("0")

    for line in lines_qs:
        qty = _dec(getattr(line, "quantity", 0))
        price = _dec(getattr(line, price_field, 0))
        base = qty * price
        subtotal += base

        # taxes is M2M on InvoiceLine
        if hasattr(line, "taxes"):
            for tax in line.taxes.all():
                rate = _dec(getattr(tax, "rate", 0))  # ✅ field name: rate
                tax_total += (base * rate / Decimal("100"))

    invoice.subtotal_amount = subtotal
    invoice.tax_amount = tax_total
    invoice.total_amount = subtotal + tax_total
    invoice.save(update_fields=["subtotal_amount", "tax_amount", "total_amount"])



def generate_invoice_from_job(job):
    """
    CORE LOGIC (final):
    - 1 JobOrder = 1 Invoice
    - 1 Job = 1 Service (wajib)
    - 1 Invoice = 1 Line (service line)
    - Taxes di header deprecated -> taxes dihitung dari InvoiceLine.taxes
    """
    if getattr(job, "is_invoiced", False) and job.invoices.exists():
        return job.invoices.order_by("-id").first()

    job_service_id = getattr(job, "service_id", None)
    if not job_service_id:
        raise ValidationError("Job Order belum punya Service. Isi Service di Job dulu sebelum generate invoice.")

    description = build_invoice_description_from_job(job) or f"Job Order {job.number}"

    JobFKModel = Invoice._meta.get_field("job_order").remote_field.model
    job_fk = job if isinstance(job, JobFKModel) else JobFKModel.objects.get(pk=job.pk)


    with transaction.atomic():
        # ✅ buat invoice (tax_amount jangan diisi legacy; nanti dihitung)
        invoice = Invoice.objects.create(
            job_order=job_fk,
            invoice_date=getattr(job, "job_date", None),
            due_date=getattr(job, "job_date", None),
            status=Invoice.ST_DRAFT,  # kalau mau DRAFT, ganti ke status draft om
            subtotal_amount=0,
            tax_amount=0,
            total_amount=0,
            notes_internal=f"Generated from JobOrder {job.number}",
            customer_id=getattr(job, "customer_id", None),
        )

        price_field = detect_line_price_field()

        line = InvoiceLine.objects.create(
            invoice=invoice,
            description=description,
            quantity=getattr(job, "quantity", None) or 1,
            uom="",
            service_id=job_service_id,  # ✅ WAJIB
            **{price_field: getattr(job, "total_amount", 0) or 0},
        )

        # ✅ copy default taxes dari service → line.taxes
        svc = getattr(job, "service", None)
        if svc and hasattr(svc, "taxes"):
            line.taxes.set(svc.taxes.all())

        if hasattr(job, "is_invoiced"):
            job.is_invoiced = True
            job.save(update_fields=["is_invoiced"])

        recalc_invoice_totals(invoice)

    return invoice
