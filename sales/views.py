from datetime import date as _date
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.forms import inlineformset_factory

from .forms import QuotationHeaderForm, QuotationLineForm, BaseLineFormSet
from .models import SalesQuotation, SalesQuotationLine, SalesNumberSequence

VER = "fq-2step-dyn-v1"

def ping(request):
    return HttpResponse(f"pong {VER}")

def _next_sequence_number():
    period = _date.today().strftime("%Y%m")
    with transaction.atomic():
        seq, _ = SalesNumberSequence.objects.select_for_update().get_or_create(
            business_type="freight", period=period, defaults={"prefix": "FQ", "padding": 5, "last_no": 0}
        )
        seq.last_no += 1
        seq.save(update_fields=["last_no"])
        return f"{seq.prefix}{seq.period}-{str(seq.last_no).zfill(seq.padding)}"

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
                obj.save()
            return redirect("sales:freight_quotation_add_lines", pk=obj.pk)
    else:
        form = QuotationHeaderForm()
    return render(request, "freight/quotation_step1.html", {"form": form})

def quotation_add_lines(request, pk: int):
    quotation = get_object_or_404(SalesQuotation, pk=pk)

    LineFormSet = inlineformset_factory(
        parent_model=SalesQuotation,
        model=SalesQuotationLine,
        form=QuotationLineForm,
        formset=BaseLineFormSet,   # <— validasi minimal 1 line
        fk_name="sales_quotation", # <— FK di model line
        extra=1,                   # <— mulai 1 baris
        can_delete=True,
    )

    if request.method == "POST":
        formset = LineFormSet(request.POST, instance=quotation)
        if formset.is_valid():
            with transaction.atomic():
                formset.save()
            messages.success(request, f"Quotation #{quotation.pk} berhasil dibuat.")
            return redirect("sales:freight_quotation_list")
    else:
        formset = LineFormSet(instance=quotation)

    return render(request, "freight/quotation_step2.html", {"formset": formset, "quotation": quotation})

def freight_quotation_list(request):
    qs = SalesQuotation.objects.order_by("-id")[:200]
    return render(request, "freight/quotation_list.html", {"quotations": qs})
