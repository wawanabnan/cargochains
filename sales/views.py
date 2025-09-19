from datetime import date as _date
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.forms import inlineformset_factory

from .forms import QuotationHeaderForm #QuotationLineForm, BaseLineFormSet
from .models import SalesQuotation, SalesQuotationLine, SalesNumberSequence
from decimal import Decimal
from geo.models import Location   # <--- tambahin ini
from sales.models import UOM


VER = "fq-2step-dyn-v1"

def ping(request):
    return HttpResponse(f"pong {VER}")

def debug_status(request):
    return HttpResponse("debug ok")

def _next_sequence_number():
    period = _date.today().strftime("%Y%m")
    with transaction.atomic():
        seq, _ = SalesNumberSequence.objects.select_for_update().get_or_create(
            business_type="freight", period=period, defaults={"prefix": "FQ", "padding": 5, "last_no": 0}
        )
        seq.last_no += 1
        seq.save(update_fields=["last_no"])
        return f"{seq.prefix}{seq.period}-{str(seq.last_no).zfill(seq.padding)}"

def _make_line_formset():
    return inlineformset_factory(
        parent_model=SalesQuotation,
        model=SalesQuotationLine,
        form=QuotationLineForm,
        formset=BaseLineFormSet,
        fk_name="sales_quotation",  # sesuai nama FK di model line
        extra=1,
        can_delete=True,
    )

def quotation_add_header(request):
    if request.method == "POST":
        form = QuotationHeaderForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                obj = form.save(commit=False)
                if not getattr(obj, "date", None):
                    obj.date = _date.today()
                if not getattr(obj, "number", None) or str(getattr(obj, "number")).strip() == "":
                    obj.number = _next_sequence_number()
                obj.total_amount = 0  # ← set 0 saat buat header
                obj.save()
            # simpan pk di session supaya bisa pakai URL tanpa pk
            request.session["current_quotation_pk"] = obj.pk
            return redirect("sales:freight_quotation_add_lines_session")
    else:
        form = QuotationHeaderForm()
    return render(request, "freight/quotation_step1.html", {"form": form})


def quotation_add_lines(request, pk: int):
    quotation = get_object_or_404(SalesQuotation, pk=pk)
    LineFormSet = _make_line_formset()
    if request.method == "POST":
        formset = LineFormSet(request.POST, instance=quotation)
        if formset.is_valid():
            with transaction.atomic():
                formset.save()
                quotation.recalc_totals() 
            messages.success(request, f"Quotation #{quotation.pk} berhasil dibuat.")
            return redirect("sales:freight_quotation_list")
    else:
        formset = LineFormSet(instance=quotation)
    return render(request, "freight/quotation_step2.html", {"formset": formset, "quotation": quotation})

def quotation_add_lines_manual_session(request):
    pk = request.session.get("current_quotation_pk")
    if not pk:
        messages.warning(request, "Session quotation hilang. Mulai dari Step-1.")
        return redirect("sales:freight_quotation_add")
    return quotation_add_lines_manual(request, pk)

def _parse_dec_id(s: str) -> Decimal:
    """'1.234,56' -> Decimal('1234.56'); aman untuk empty."""
    if s is None: return Decimal("0")
    s = str(s).strip()
    if not s: return Decimal("0")
    # hilangkan ribuan, ganti koma jadi titik
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")
    

def quotation_add_lines_manual(request, pk: int):
    quotation = get_object_or_404(SalesQuotation, pk=pk)
    # list pilihan untuk dropdown
    locations = Location.objects.all().order_by("name")
    uoms = UOM.objects.all().order_by("name")

    if request.method == "POST":
        origins = request.POST.getlist("origin[]")
        dests   = request.POST.getlist("destination[]")
        descs   = request.POST.getlist("description[]")
        uom_ids = request.POST.getlist("uom[]")
        qtys    = request.POST.getlist("qty[]")
        prices  = request.POST.getlist("price[]")

        lines_to_create = []
        total = Decimal("0.00")
        any_valid = False

        # hapus semua line lama, lalu buat ulang (sederhana & konsisten)
        with transaction.atomic():
            SalesQuotationLine.objects.filter(sales_quotation=quotation).delete()

            for i in range(max(len(origins), len(dests), len(descs), len(uom_ids), len(qtys), len(prices))):
                origin_id = (origins[i] if i < len(origins) else "") or ""
                dest_id   = (dests[i]   if i < len(dests)   else "") or ""
                uom_id    = (uom_ids[i] if i < len(uom_ids) else "") or ""
                description = (descs[i] if i < len(descs) else "").strip()
                qty  = _parse_dec_id(qtys[i] if i < len(qtys) else "0")
                price= _parse_dec_id(prices[i] if i < len(prices) else "0")

                # lewati baris kosong total
                if not (origin_id or dest_id or description or qty or price or uom_id):
                    continue

                # minimal isi: origin, destination, uom, qty>0
                if not origin_id or not dest_id or not uom_id or qty <= 0:
                    # bisa ditambahkan kumpulan error per-baris jika perlu
                    continue

                try:
                    origin = Location.objects.get(pk=origin_id)
                    dest   = Location.objects.get(pk=dest_id)
                    uom    = UOM.objects.get(pk=uom_id)
                except (Location.DoesNotExist, Uom.DoesNotExist):
                    continue

                line_total = qty * price
                total += line_total
                any_valid = True
                lines_to_create.append(SalesQuotationLine(
                    sales_quotation=quotation,
                    origin=origin,
                    destination=dest,
                    description=description,
                    qty=qty,
                    uom=uom,
                    price=price,
                ))

            if not any_valid:
                messages.error(request, "Minimal satu line valid harus diisi.")
            else:
                SalesQuotationLine.objects.bulk_create(lines_to_create)
                quotation.total_amount = total
                quotation.save(update_fields=["total_amount"])
                messages.success(request, f"Quotation #{quotation.number} tersimpan. Grand total: {total:.2f}")
                return redirect("sales:freight_quotation_list")

    # GET atau POST invalid → render ulang
    # siapkan data baris awal: kalau belum ada, tampilkan 1 baris kosong
    existing = list(SalesQuotationLine.objects.filter(sales_quotation=quotation))

    return render(request, "freight/quotation_step2.html", {
        "quotation": quotation,
        "locations": locations,
        "uoms": uoms,
        "lines": existing,
    })


def freight_quotation_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = SalesQuotation.objects.all().select_related("customer", "currency").order_by("-id")
    if q:
        qs = qs.filter(
            Q(number__icontains=q) |
            Q(customer__name__icontains=q)
        )
    qs = qs[:200]  # batasi 200 terbaru
    return render(request, "freight/quotation_list.html", {"quotations": qs, "q": q})
