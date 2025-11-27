# sales/views/freight_quotation.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from sales.forms import FreightQuotationForm
from sales.freight import FreightQuotation, FreightQuotationStatus

@login_required
def freight_quotation_add(request):
    if request.method == "POST":
        form = FreightQuotationForm(request.POST)
        if form.is_valid():
            quotation = form.save(commit=False)
            quotation.created_by = request.user  # kalau ada field ini
            # status default DRAFT
            if not quotation.status:
                quotation.status = FreightQuotationStatus.DRAFT
            quotation.save()
            messages.success(request, f"Quotation {quotation.number} berhasil dibuat.")
            return redirect("sales:freight_quotation_detail", pk=quotation.pk)
    else:
        form = FreightQuotationForm()

    context = {
        "form": form,
        "mode": "add",
        "page_title": "Add Freight Quotation",
    }
    return render(request, "sales/freight_quotation_form.html", context)
