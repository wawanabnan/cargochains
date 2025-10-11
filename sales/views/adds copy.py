# sales/views/adds.py
from datetime import date as _date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from sales.forms import QuotationHeaderForm
from sales import models as m
from geo.models import Location
from decimal import Decimal, ROUND_HALF_UP

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
from datetime import date
from core.models import NumberSequence
from core.numbering import next_number

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

            # === generate nomor quotation ===
            business_type = (cd.get("business_type") or "freight").lower()
            SEQ_CODE_BY_TYPE = {
                "freight": "QUOTATION_FREIGHT",
                "charter": "QUOTATION_CHARTER",
            }
            seq_code = SEQ_CODE_BY_TYPE.get(business_type, "QUOTATION_FREIGHT")

            seq_qs = NumberSequence.objects.filter(app_label="sales", code=seq_code)
            
            header_session["number"] = next_number(seq_qs, today=date.today())
            header_session["sales_user_id"] = request.user.id
            # ================================
    
            request.session["quotation_header_data"] = header_session
            return redirect("sales:quotation_add_lines")
    else:
        form = QuotationHeaderForm()
    return render(request, "freight/quotation_step1.html", {"form": form})


# ===== STEP 2: LINES -> saveAll (atomic) =====
@transaction.atomic
def quotation_add_lines(request):
    # SENTINEL
    from django.contrib import messages
    from django.shortcuts import render, redirect
    from django.db import transaction
    from sales import models as m
    from geo.models import Location

    SESSION_KEY = "quotation_header_data"

    # helper fallback: parse decimal
    def _pdec(x):
        try:
            x = (x or "").strip()
            if not x:
                return Decimal("0")
            return Decimal(x.replace(".", "").replace(",", "."))
        except Exception:
            return Decimal("0")

    header_data = request.session.get(SESSION_KEY)
    if not header_data:
        messages.warning(request, "Step-1 belum diisi.")
        return redirect("sales:quotation_add")

    # Rebuild kwargs header (ikut pola yang lama)
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
        # Baca nama field versi lama & alternatif (jaga-jaga)
        def L(name):
            vals = request.POST.getlist(name)
            return vals if vals else request.POST.getlist(name.rstrip("[]"))
        origins = L("origin[]")
        dests   = L("destination[]")
        descs   = L("description[]")
        uom_ids = L("uom[]")
        qtys    = L("qty[]")
        prices  = L("price[]")

        # ===== VALIDASI AWAL — stop kalau invalid (tanpa save) =====
        rows = max(len(origins), len(dests), len(descs), len(uom_ids), len(qtys), len(prices)) or 0
        incomplete_rows, has_valid = [], False
        for i in range(rows):
            origin_id = (origins[i] if i < len(origins) else "").strip()
            dest_id   = (dests[i]   if i < len(dests)   else "").strip()
            uom_id    = (uom_ids[i] if i < len(uom_ids) else "").strip()
            qty_raw   = (qtys[i]    if i < len(qtys)    else "").strip()
            price_raw = (prices[i]  if i < len(prices)  else "")
            desc      = ((descs[i] if i < len(descs) else "") or "").strip()

            any_filled = any([origin_id, dest_id, uom_id, qty_raw, price_raw, desc])
            qty = _pdec(qty_raw)
            full_ok = all([origin_id, dest_id, uom_id]) and (qty > 0)  # tambahkan `and desc` kalau deskripsi wajib

            if any_filled and not full_ok:
                incomplete_rows.append(i + 1)
            if full_ok:
                has_valid = True

        if incomplete_rows:
            messages.error(
                request,
                "Baris belum lengkap: {}. Lengkapi atau kosongkan sepenuhnya."
                .format(", ".join(map(str, incomplete_rows)))
            )
            return render(request, "freight/quotation_step2.html",
                          {"quotation": header_data, "locations": locations, "uoms": uoms, "lines": []})

        if not has_valid:
            messages.error(request, "Minimal satu line valid harus diisi.")
            return render(request, "freight/quotation_step2.html",
                          {"quotation": header_data, "locations": locations, "uoms": uoms, "lines": []})
        # ===== END VALIDASI =====

        # ===== SIMPAN (ATOMIK) SETELAH LOLOS VALIDASI =====
        with transaction.atomic():
            # Buat header
            quotation = m.SalesQuotation(**hdr_kwargs)

            # tanggal default
            if not getattr(quotation, "date", None):
                quotation.date = _date.today()

            # set SALES PERSON ke kolom yang benar (punyamu: sales_user_id)
            if hasattr(quotation, "sales_user_id") and not getattr(quotation, "sales_user_id", None):
                quotation.sales_user_id = header_data.get("sales_user_id", request.user.id)

            # nomor (pakai yang ada, atau generate)
            if not getattr(quotation, "number", None):
                quotation.number = _next_sequence_number()

            # nomor unik (hindari IntegrityError 1062)
            attempts = 0
            while m.SalesQuotation.objects.filter(number=quotation.number).exists():
                attempts += 1
                quotation.number = _next_sequence_number()
                if attempts >= 5:
                    messages.error(request, "Gagal membuat nomor unik untuk quotation. Coba lagi.")
                    return render(request, "freight/quotation_step2.html",
                                  {"quotation": header_data, "locations": locations, "uoms": uoms, "lines": []})

            # init total
            quotation.total = Decimal("0.00")
            quotation.vat = Decimal("0.00")
            quotation.grand_total = Decimal("0.00")
            quotation.total_amount = Decimal("0.00")

            quotation.save()

            # Lines
            total = Decimal("0.00")
            lines_to_create = []
            for i in range(rows):
                origin_id = (origins[i] if i < len(origins) else "") or ""
                dest_id   = (dests[i]   if i < len(dests)   else "") or ""
                uom_id    = (uom_ids[i] if i < len(uom_ids) else "") or ""
                description = ((descs[i] if i < len(descs) else "") or "").strip()
                qty   = _pdec(qtys[i]   if i < len(qtys)   else "0")
                price = _pdec(prices[i] if i < len(prices) else "0")

                if not (origin_id and dest_id and uom_id and qty > 0):
                    continue

                origin = Location.objects.get(pk=origin_id)
                dest   = Location.objects.get(pk=dest_id)
                uom    = m.UOM.objects.get(pk=uom_id)

                line_total = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total += line_total

                lines_to_create.append(
                    m.SalesQuotationLine(
                        sales_quotation=quotation,
                        origin=origin,
                        destination=dest,
                        description=description,
                        qty=qty,
                        uom=uom,
                        price=price,
                        amount=line_total,
                    )
                )

            if not lines_to_create:
                messages.error(request, "Minimal satu line valid harus diisi.")
                return render(request, "freight/quotation_step2.html",
                              {"quotation": header_data, "locations": locations, "uoms": uoms, "lines": []})

            m.SalesQuotationLine.objects.bulk_create(lines_to_create)

            # Update total header
            subtotal = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            quotation.total = subtotal
            quotation.vat = quotation.vat or Decimal("0.00")
            quotation.grand_total = (quotation.total + quotation.vat).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            quotation.total_amount = quotation.total
            quotation.save(update_fields=["total", "vat", "grand_total", "total_amount"])

            # bersihkan session
            request.session.pop(SESSION_KEY, None)

        messages.success(request, f"Quotation {quotation.number} berhasil dibuat. Grand Total {quotation.grand_total}")
        return redirect("sales:quotation_list")

    # GET
    return render(
        request,
        "freight/quotation_step2.html",
        {"quotation": header_data, "locations": locations, "uoms": uoms, "lines": []},
    )
