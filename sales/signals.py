# sales/signals.py
from decimal import Decimal
from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import SalesQuotationLine, SalesOrder
from projects.models import Project, ProjectCategory


# ======================================================================
# A) Recalculate total quotation whenever quotation lines change
# ======================================================================

def _recalc_header(instance):
    header = instance.sales_quotation
    if getattr(header, "id", None):
        header.recalc_totals()

@receiver(post_save, sender=SalesQuotationLine)
def _line_saved(sender, instance, **kwargs):
    _recalc_header(instance)

@receiver(post_delete, sender=SalesQuotationLine)
def _line_deleted(sender, instance, **kwargs):
    _recalc_header(instance)


# ======================================================================
# B) Auto-generate Project(s) per ORDER LINE when SalesOrder goes DRAFT → CONFIRMED
# ======================================================================

CONFIRM_STATES = {"CONFIRMED"}

CATEGORY_MAP = {
    "REGULAR SHIPMENT": ("REGULAR", "Regular Shipment"),
    "PROJECT SHIPMENT": ("PROJECT", "Project Shipment"),
    "SHIP CHARTER":     ("CHARTER", "Ship Charter"),
    "SHIP MANAGEMENT":  ("MGMT", "Ship Management"),
    "AGENCY":           ("AGENCY", "Agency"),
}

def _ensure_category_for(order) -> ProjectCategory:
    """
    - Jika order berasal dari Freight Quotation ⇒ Regular Shipment
    - Jika tidak, mapping berdasarkan sales_service.name
    - Fallback "SO" / "Sales Order"
    """
    if getattr(order, "sales_quotation_id", None):
        code, name = ("REGULAR", "Regular Shipment")
        cat, _ = ProjectCategory.objects.get_or_create(code=code, defaults={"name": name})
        return cat

    service_name = ""
    if getattr(order, "sales_service", None):
        service_name = (getattr(order.sales_service, "name", "") or "").upper().strip()

    code, name = CATEGORY_MAP.get(service_name, ("SO", "Sales Order"))
    cat, _ = ProjectCategory.objects.get_or_create(code=code, defaults={"name": name})
    return cat


def _project_ref_for_line(order, line) -> str:
    """Ref unik per line agar idempotent: <SO-number>-L<line.id>."""
    return f"{order.number}-L{line.id}"

def _project_exists_for_line(order, line) -> bool:
    return Project.objects.filter(ref_number=_project_ref_for_line(order, line)).exists()


def _od_string_from_line(line) -> str:
    """Nama origin/destination dari line."""
    origin = getattr(line.origin, "name", None) or str(line.origin)
    dest   = getattr(line.destination, "name", None) or str(line.destination)
    return f"{origin or '-'} - {dest or '-'}"


def _build_project_name_for_line(category_obj: ProjectCategory, order, line) -> str:
    cat = category_obj.name
    od  = _od_string_from_line(line)
    svc = getattr(order.sales_service, "name", None) if getattr(order, "sales_service", None) else None
    return f"{cat}: {od} · {svc}" if svc else f"{cat}: {od}"


def _extract_order_value(order):
    """
    Ambil grand total & currency dari SalesOrder (beberapa kemungkinan nama field).
    Return: (Decimal amount, currency_code:str)
    """
    candidates_amount = [
        getattr(order, "grand_total", None),
        getattr(order, "total_grand", None),
        getattr(order, "total_amount", None),
        getattr(order, "amount_total", None),
        getattr(order, "total", None),
        getattr(order, "grand_total_idr", None),
    ]
    amount = next((a for a in candidates_amount if a is not None), Decimal("0.00"))

    cur_obj = getattr(order, "currency", None)
    currency_code = getattr(cur_obj, "code", None) or getattr(order, "currency_code", None) or "IDR"
    return (amount or Decimal("0.00")), currency_code


def _extract_line_value(order, line, default_amount_per_line: Decimal, currency_code: str):
    """
    Ambil nilai per line jika tersedia; jika tidak, fallback = grand_total / jumlah line.
    Boleh override currency jika line punya currency sendiri.
    """
    candidates_amount = [
        getattr(line, "grand_total", None),
        getattr(line, "total_amount", None),
        getattr(line, "amount_total", None),
        getattr(line, "line_total", None),
        getattr(line, "total", None),
    ]
    amount = next((a for a in candidates_amount if a is not None), None)
    if amount is None:
        amount = default_amount_per_line

    line_cur = getattr(line, "currency", None)
    if line_cur is not None:
        currency_code = getattr(line_cur, "code", None) or str(line_cur) or currency_code

    return amount or Decimal("0.00"), currency_code or "IDR"


def _build_project_payload_for_line(order, line):
    """
    Susun payload Project untuk 1 order line:
    - Nama, kategori, status, start_date, deskripsi
    - Nilai project (amount + currency)
    - Ref unik per line
    """
    cat = _ensure_category_for(order)
    name = _build_project_name_for_line(cat, order, line)

    qref = ""
    if getattr(order, "sales_quotation", None):
        qnum = getattr(order.sales_quotation, "number", "")
        if qnum:
            qref = f" from Quotation {qnum}"

    grand_amount, grand_curr = _extract_order_value(order)
    line_count = max(order.lines.count(), 1)
    default_per_line = (grand_amount / line_count) if line_count > 0 else Decimal("0.00")
    value_amount, value_curr = _extract_line_value(order, line, default_per_line, grand_curr)

    # start_date = tanggal konfirmasi (pakai confirmed_at kalau ada)
    start_date = timezone.localdate()
    if hasattr(order, "confirmed_at") and order.confirmed_at:
        try:
            start_date = order.confirmed_at.date()
        except Exception:
            pass

    return dict(
        category=cat,
        ref_number=_project_ref_for_line(order, line),
        name=name,
        status=Project.STATUS_CONFIRMED,           # seragam dengan Sales
        start_date=start_date,
        description=f"Auto-generated{qref} for Sales Order {order.number} (Line {line.id})",
        value_amount=value_amount,
        value_currency_code=value_curr,
    )


@receiver(pre_save, sender=SalesOrder)
def create_projects_per_line_when_so_confirmed(sender, instance: SalesOrder, **kwargs):
    """
    Saat SalesOrder transisi DRAFT → CONFIRMED:
    - Buat Project per LINE (1 line = 1 project).
    - Idempotent via ref_number "<SO>-L<line.id>".
    """
    if not instance.pk:
        return

    try:
        old = sender.objects.only("status", "number").get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_status = (old.status or "").upper()
    new_status = (instance.status or "").upper()
    if not (old_status == "DRAFT" and new_status in CONFIRM_STATES):
        return

    lines_qs = instance.lines.select_related("origin", "destination")
    if not lines_qs.exists():
        return

    with transaction.atomic():
        for line in lines_qs:
            if _project_exists_for_line(instance, line):
                continue
            payload = _build_project_payload_for_line(instance, line)
            Project.objects.create(**payload)
