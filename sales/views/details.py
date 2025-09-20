from django.shortcuts import render, get_object_or_404
from sales import models as m

def quotation_detail(request, pk):
    quotation = get_object_or_404(
        m.SalesQuotation.objects.select_related(
            "customer", "sales_service", "currency", "payment_term"
        ),
        pk=pk,
    )
    lines = (
        m.SalesQuotationLine.objects
        .select_related("origin", "destination", "uom")
        .filter(sales_quotation=quotation)
        .order_by("id")
    )
    return render(request, "freight/quotation_detail.html", {
        "quotation": quotation,
        "lines": lines,
    })
