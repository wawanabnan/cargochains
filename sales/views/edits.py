# sales/views/edits.py
from django.views.generic import UpdateView
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from .. import models as m
from ..forms import QuotationHeaderForm
from django.forms import inlineformset_factory   # ← tambahkan ini
from ..forms_lines_edit import LineEditForm, LineEditFormSet
   # ← pakai form kustom



ALLOWED_EDIT_STATUSES = {"draft", "sent"}

LineFormSet = inlineformset_factory(
    parent_model=m.SalesQuotation,
    model=m.SalesQuotationLine,
    form=LineEditForm,
    formset=LineEditFormSet,   # ← kunci isi initial text
    can_delete=True,
    extra=0,
   
)

class FreightQuotationEditView(UpdateView):
    model = m.SalesQuotation
    form_class = QuotationHeaderForm
    template_name = "freight/quotation_edit.html"
    context_object_name = "quotation"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        status_val = (self.object.status or "").lower()
        if status_val not in ALLOWED_EDIT_STATUSES:
            messages.warning(request, f"Tidak bisa diedit. Status: {self.object.status}")
            return redirect("quotation_detail", pk=self.object.pk)  # sesuaikan rute detail kamu
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data_old(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "edit"
        ctx["lock_number"] = True
        ctx["formset"] = LineFormSet(instance=self.object, prefix="lines")  # ✅ di sini tempatnya

        # Jika template butuh daftar uoms di <template id="tpl-line">
        # ctx["uoms"] = m.UoM.objects.all().order_by("name")
        
        return ctx
    

    from decimal import Decimal, ROUND_HALF_UP
    from django.db.models import Sum

    def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx["mode"] = "edit"
            ctx["lock_number"] = True
            ctx["formset"] = LineFormSet(instance=self.object, prefix="lines")

            # --- HITUNG NILAI DARI LINES YANG SUDAH ADA DI DB ---
            # kalau kolom amount sudah tersimpan per line, tinggal sum('amount')
            subtotal = self.object.salesquotationline_set.aggregate(
                s=Sum('amount')
            )['s'] or Decimal('0')

            # kalau kamu lebih yakin hitung ulang: qty * price
            # from django.db.models import F, DecimalField, ExpressionWrapper
            # subtotal = (self.object.salesquotationline_set
            #   .aggregate(s=Sum(ExpressionWrapper(F('qty')*F('price'),
            #                                      output_field=DecimalField(max_digits=18, decimal_places=2))))['s']
            #   or Decimal('0'))

            tax_rate = Decimal(self.object.tax_rate or 0)        # asumsi ada field tax_rate (%) di header
            tax_amount = (subtotal * tax_rate / Decimal('100')).quantize(Decimal('0.01'), ROUND_HALF_UP)
            grand_total = (subtotal + tax_amount).quantize(Decimal('0.01'), ROUND_HALF_UP)

            ctx.update({
                "init_subtotal":    subtotal.quantize(Decimal('0.01'), ROUND_HALF_UP),
                "init_tax_rate":    tax_rate,
                "init_tax_amount":  tax_amount,
                "init_grand_total": grand_total,
            })
            return ctx


    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()  # nomor tidak diubah

        POST = self.request.POST
        origins      = POST.getlist("origin[]")        # hidden IDs
        destinations = POST.getlist("destination[]")   # hidden IDs
        descriptions = POST.getlist("description[]")
        uoms         = POST.getlist("uom[]")
        qtys         = POST.getlist("qty[]")
        prices       = POST.getlist("price[]")

        def to_decimal(s):
            if s is None: return 0
            s = str(s).strip()
            if not s: return 0
            lc, ld = s.rfind(',')   , s.rfind('.')
            if lc > ld:  s = s.replace('.', '').replace(',', '.')
            else:        s = s.replace(',', '')
            try: return float(s)
            except: return 0

        new_lines = []
        n = max(len(origins), len(destinations), len(descriptions), len(uoms), len(qtys), len(prices))
        for i in range(n):
            origin_id = (origins[i] if i < len(origins) else "").strip()
            dest_id   = (destinations[i] if i < len(destinations) else "").strip()
            desc      = (descriptions[i] if i < len(descriptions) else "").strip()
            uom_id    = (uoms[i] if i < len(uoms) else "").strip()
            qty       = to_decimal(qtys[i] if i < len(qtys) else "")
            price     = to_decimal(prices[i] if i < len(prices) else "")

            if not any([origin_id, dest_id, uom_id, desc, qty, price]):
                continue
            if not origin_id or not dest_id or not uom_id or qty <= 0:
                continue

            amount = round(qty * price, 2)
            new_lines.append(m.SalesQuotationLine(
                quotation=self.object,
                origin_id=origin_id or None,
                destination_id=dest_id or None,
                description=desc or "",
                uom_id=uom_id or None,
                qty=qty,
                price=price,
                amount=amount,
            ))

        if not new_lines:
            messages.error(self.request, "Minimal satu baris line yang lengkap diperlukan.")
            return self.form_invalid(form)

        m.SalesQuotationLine.objects.filter(quotation=self.object).delete()
        m.SalesQuotationLine.objects.bulk_create(new_lines, batch_size=100)

        messages.success(self.request, f"Quotation {self.object.number} berhasil diperbarui.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("quotation_edit", kwargs={"pk": self.object.pk})
