# sales/views/adds.py
from datetime import date as _date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from sales.forms import QuotationHeaderForm
from sales import models as m
from geo.models import Location

MODEL_MAP = {
    "customer": m.Partner,
    "sales_agency": m.Partner,
    "sales_service": m.SalesService,
    "currency": m.Currency,
    "payment_term": m.PaymentTerm,
}

def _next_sequence_number() -> str:
    period = _date.today().strftime("%Y%m")
    with transaction.atomic():
        seq, _ = m.SalesNumberSequence.objects.select_for_update().get_or_create(
            business_type="freight",
            period=period,
            defaults={"prefix": "FQ", "padding": 5, "last_no": 0},
        )
        seq.last_no += 1
        seq.save(update_fields=["last_no"])
        return f"{seq.prefix}{seq.period}-{str(seq.last_no).zfill(seq.padding)}"

def _parse_dec_id(s: str) -> Decimal:
    if not s:
        return Decimal("0")
    s = str(s).strip()
    if not s:
        return Decimal("0")
    # terima "1.234,56" atau "1234.56"
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")

def _parse_iso_date_safe(v) -> _date | None:
    # aman untuk "", None, dan format salah. tanpa slice [:10]
    if not v:
        return None
    if hasattr(v, "isoformat"):  # sudah date
        return v
    v = str(v).strip()
    if not v:
        return None
    # coba fromisoformat (YYYY-MM-DD)
    try:
        return _date.fromisoformat(v.split("T")[0])  # dukung yyyy-mm-ddThh:mm
    except Exception:
        # fallback manual
        parts = v.split("-")
        if len(parts) >= 3:
            try:
                y, mth, d = int(parts[0]), int(parts[1]), int(parts[2][:2])
                return _date(y, mth, d)
            except Exception:
                return None
        return None

# ===== STEP 1: HEADER -> simpan di session (serialize) =====
def quotation_add_header(request):
    if request.method == "POST":
        form = QuotationHeaderForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            header_session = {}
            for k, v in cd.items():
                if v is None:
                    header_session[k] = None
                elif hasattr(v, "isoformat"):  # date/datetime
                    header_session[k] = v.isoformat()
                elif hasattr(v, "id"):        # FK -> simpan *_id
                    header_session[f"{k}_id"] = v.id
                else:
                    header_session[k] = v
            request.session["quotation_header_data"] = header_session
            return redirect("sales:quotation_add_lines")
    else:
        form = QuotationHeaderForm()
    return render(request, "freight/quotation_step1.html", {"form": form})

# ===== STEP 2: LINES -> saveAll (atomic) =====
@transaction.atomic
def quotation_add_lines(request):
    header_data = request.session.get("quotation_header_data")
    if not header_data:
        messages.warning(request, "Step-1 belum diisi.")
        return redirect("sales:quotation_add")

    # rebuild kwargs header dari session (FK: *_id -> objek)
    hdr_kwargs = {}
    for k, v in header_data.items():
        if k.endswith("_id"):
            field = k[:-3]
            model_cls = MODEL_MAP.get(field)
            if model_cls and v is not None:
                try:
                    hdr_kwargs[field] = model_cls.objects.get(pk=v)
                except model_cls.DoesNotExist:
                    hdr_kwargs[field] = None
            else:
                hdr_kwargs[field] = None
        elif k in ("valid_until", "date"):
            hdr_kwargs[k] = _parse_iso_date_safe(v)
        else:
            hdr_kwargs[k] = v

    locations = Location.objects.all().order_by("name")
    uoms = m.UOM.objects.all().order_by("name")

    if request.method == "POST":
        origins = request.POST.getlist("origin[]")
        dests   = request.POST.getlist("destination[]")
        descs   = request.POST.getlist("description[]")
        uom_ids = request.POST.getlist("uom[]")
        qtys    = request.POST.getlist("qty[]")
        prices  = request.POST.getlist("price[]")

        # buat header
        quotation = m.SalesQuotation(**hdr_kwargs)
        if not getattr(quotation, "date", None):
            quotation.date = _date.today()
        if not getattr(quotation, "number", None):
            quotation.number = _next_sequence_number()
        quotation.total_amount = Decimal("0.00")
        quotation.save()

        rows = max(len(origins), len(dests), len(descs), len(uom_ids), len(qtys), len(prices))
        lines_to_create, total, any_valid = [], Decimal("0.00"), False

        for i in range(rows):
            origin_id = (origins[i] if i < len(origins) else "") or ""
            dest_id   = (dests[i]   if i < len(dests)   else "") or ""
            uom_id    = (uom_ids[i] if i < len(uom_ids) else "") or ""
            description = ((descs[i] if i < len(descs) else "") or "").strip()
            qty   = _parse_dec_id(qtys[i]   if i < len(qtys)   else "0")
            price = _parse_dec_id(prices[i] if i < len(prices) else "0")

            # lewati baris kosong atau tidak valid
            if not (origin_id and dest_id and uom_id and qty > 0):
                continue

            origin = Location.objects.get(pk=origin_id)
            dest   = Location.objects.get(pk=dest_id)
            uom    = m.UOM.objects.get(pk=uom_id)

            line_total = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += line_total
            any_valid = True

            lines_to_create.append(
                m.SalesQuotationLine(
                    sales_quotation=quotation,
                    origin=origin,
                    destination=dest,
                    description=description,
                    qty=qty,
                    uom=uom,
                    price=price,
                    amount=line_total,   # PASTIKAN TERSIMPAN
                )
            )

        if not any_valid:
            # trigger rollback seluruh transaksi
            raise ValueError("Minimal satu line valid harus diisi.")

        # simpan lines & update total
        m.SalesQuotationLine.objects.bulk_create(lines_to_create)
        quotation.total_amount = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        quotation.save(update_fields=["total_amount"])

        # bersihkan session
        request.session.pop("quotation_header_data", None)
        messages.success(request, f"Quotation {quotation.number} berhasil dibuat. Total {quotation.total_amount}")
        return redirect("sales:quotation_list")

    # GET → render form lines
    return render(
        request,
        "freight/quotation_step2.html",
        {"quotation": header_data, "locations": locations, "uoms": uoms, "lines": []},
    )
