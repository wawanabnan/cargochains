# sales/views/adds.py
from datetime import date as _date
from decimal import Decimal, ROUND_HALF_UP, getcontext
import re

from django import forms
from django.forms import formset_factory
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from django.db import transaction

from sales.forms.quotations import QuotationHeaderForm
from sales import models as m
from geo.models import Location
from core.models.settings import CoreSetting
from core.utils import get_next_number

getcontext().prec = 28
DEC2 = Decimal("0.01")


# ────────────────────────────────────────────────────────────────────────────
# Helpers: parser angka ID & tax rate dari Core Settings
# ────────────────────────────────────────────────────────────────────────────
def _to_decimal_id(value) -> Decimal:
    """
    Parse angka lokal ID ke Decimal:
    - "1.234,56" -> 1234.56
    - "250.000"  -> 250000
    - "11%"      -> 11
    - "Rp 1.000,00" -> 1000
    Aman untuk kosong/invalid → 0
    """
    if value is None:
        return Decimal("0")
    s = str(value).strip()
    if not s:
        return Decimal("0")

    # sisakan digit, koma, titik, minus; buang currency & persen
    s = re.sub(r"[^\d,.\-]", "", s)

    has_c = "," in s
    has_d = "." in s
    if has_c and has_d:
        # gunakan pemisah TERAKHIR sebagai desimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_c and not has_d:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")

    try:
        return Decimal(s)
    except Exception:
        return Decimal("0")


def _get_tax_rate() -> Decimal:
    """
    Ambil PPN dari CoreSettings (code='tax_rate_percent') sebagai rate desimal:
    - 11  -> 0.11
    Default 11% jika tidak ada/invalid.
    """
    pct = CoreSetting.objects.filter(code="tax_rate_percent").values_list("int_value", flat=True).first()
    try:
        pct = Decimal(str(pct if pct is not None else 11))
    except Exception:
        pct = Decimal("11")
    if pct < 0:
        pct = Decimal("11")
    return (pct / Decimal("100")).quantize(DEC2)  # 0.11


# ────────────────────────────────────────────────────────────────────────────
# View
# ────────────────────────────────────────────────────────────────────────────
from ..auth import SalesAccessRequiredMixin, sales_queryset_for_user, is_sales_supervisor
from django.views.generic import  CreateView

class FreightQuotationAddView(SalesAccessRequiredMixin,  CreateView):
    template_name = "freight/quotation_add.html"

    # ---- dummy formset agar tombol & blok template tampil ----
    def _dummy_formset(self):
        class _DummyLineForm(forms.Form):
            origin = forms.IntegerField(widget=forms.HiddenInput, required=False)
            destination = forms.IntegerField(widget=forms.HiddenInput, required=False)

            # (opsional) kalau template merender bidang-bidang ini:
            description = forms.CharField(
                required=False,
                widget=forms.Textarea(attrs={"rows": 1, "class": "form-control form-control-sm"})
            )
            uom = forms.ModelChoiceField(
                required=False,
                queryset=m.UOM.objects.all().order_by("name"),
                widget=forms.Select(attrs={"class": "form-select form-select-sm"})
            )
            qty = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={"class": "form-control form-control-sm text-end"})
            )
            price = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={"class": "form-control form-control-sm text-end"})
            )
            amount = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    "class": "form-control form-control-sm text-end js-amount",
                    "readonly": "readonly"
                })
            )

        DummyFS = formset_factory(_DummyLineForm, extra=1)
        return DummyFS(prefix="lines")

    # ---- context dropdown ----
    def _common_context(self):
        return {
            "uoms": m.UOM.objects.all().order_by("name"),
            "locations": Location.objects.all().order_by("name"),
        }

    # ---- GET ----
    def get(self, request):
        form = QuotationHeaderForm(user=request.user)
        ctx = {"form": form, "formset": self._dummy_formset()}
        ctx.update(self._common_context())
        return render(request, self.template_name, ctx)

    # ---- POST ----
    @transaction.atomic
    def post(self, request):
        form = QuotationHeaderForm(request.POST, user=request.user)

        if not form.is_valid():
            ctx = {"form": form, "formset": self._dummy_formset()}
            ctx.update(self._common_context())
            messages.error(request, "Header belum lengkap.")
            return render(request, self.template_name, ctx)

        # 1) simpan header (sementara, total akan diisi setelah hitung)
        obj: m.SalesQuotation = form.save(commit=False)
        obj.date = timezone.localdate()
        obj.sales_user = request.user

        if not getattr(obj, "number", None):
            obj.number = get_next_number("sales", "FREIGHT_QUOTATION")

        # jaga-jaga duplikat
        while m.SalesQuotation.objects.filter(number=obj.number).exists():
            obj.number = get_next_number("sales", "FREIGHT_QUOTATION")

        obj.save()

        # 2) ambil & simpan lines manual
        origins = request.POST.getlist("origin[]")
        dests   = request.POST.getlist("destination[]")
        descs   = request.POST.getlist("description[]")
        uom_ids = request.POST.getlist("uom[]")
        qtys    = request.POST.getlist("qty[]")
        prices  = request.POST.getlist("price[]")

        total = Decimal("0.00")
        rows = max(len(origins), len(dests), len(descs), len(uom_ids), len(qtys), len(prices))
        any_valid = False

        for i in range(rows):
            origin_id = (origins[i] if i < len(origins) else "").strip()
            dest_id   = (dests[i]   if i < len(dests)   else "").strip()
            uom_id    = (uom_ids[i] if i < len(uom_ids) else "").strip()
            desc      = (descs[i]   if i < len(descs)   else "") or ""

            if not (origin_id and dest_id and uom_id):
                continue

            try:
                origin = Location.objects.get(pk=origin_id)
                dest   = Location.objects.get(pk=dest_id)
                uom    = m.UOM.objects.get(pk=uom_id)
            except Exception:
                continue

            # ⬇️ gunakan parser robust (bukan hanya .replace(",",""))
            qty   = _to_decimal_id(qtys[i]   if i < len(qtys)   else None)
            price = _to_decimal_id(prices[i] if i < len(prices) else None)

            if qty <= 0:
                continue

            amount = (qty * price).quantize(DEC2, rounding=ROUND_HALF_UP)
            total += amount
            any_valid = True

            m.SalesQuotationLine.objects.create(
                sales_quotation=obj,
                origin=origin,
                destination=dest,
                description=desc,
                uom=uom,
                qty=qty.quantize(DEC2),
                price=price.quantize(DEC2),
                amount=amount,
            )

        if not any_valid:
            transaction.set_rollback(True)
            ctx = {"form": form, "formset": self._dummy_formset()}
            ctx.update(self._common_context())
            messages.error(request, "Minimal satu line valid harus diisi.")
            return render(request, self.template_name, ctx)

        # 3) total header (server as source of truth)
        rate = _get_tax_rate()                       # contoh: Decimal('0.11')
        vat  = (total * rate).quantize(DEC2, rounding=ROUND_HALF_UP)
        grand= (total + vat).quantize(DEC2, rounding=ROUND_HALF_UP)

        # jika model punya field tax_rate, set juga (opsional)
        update_fields = ["total", "vat", "grand_total", "total_amount"]
        if hasattr(obj, "tax_rate"):
            obj.tax_rate = rate
            if "tax_rate" not in update_fields:
                update_fields.append("tax_rate")

        obj.total        = total
        obj.vat          = vat
        obj.grand_total  = grand
        obj.total_amount = total
        obj.save(update_fields=update_fields)

        messages.success(request, f"Quotation {obj.number} berhasil disimpan.")
        return redirect("sales:quotation_list")
