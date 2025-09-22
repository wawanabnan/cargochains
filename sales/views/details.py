from django.shortcuts import render, get_object_or_404
from sales import models as m
from django.http import HttpResponse
from django.template.loader import render_to_string
from ..models import SalesQuotation
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from ..models import SalesQuotation
from django.conf import settings
from xhtml2pdf import pisa
import io, os



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



from ..models import SalesOrder

def order_detail(request, pk):
    so = get_object_or_404(SalesOrder.objects.select_related("customer","sales_quotation"), pk=pk)
    lines = so.lines.all() if hasattr(so, "lines") else []
    return render(request, "freight/order_details.html", {"order": so, "lines": lines})


def quotation_print(request, pk):
    q = get_object_or_404(
        SalesQuotation.objects.select_related("customer", "currency")
        .prefetch_related("lines__origin", "lines__destination", "lines__uom"),
        pk=pk
    )
    # pakai template yang ramah print (tanpa sidebar/header besar)
    return render(request, "freight/quotation_print.html", {"q": q, "is_pdf": False})



def _link_callback(uri, rel):
    """
    Resolve static file paths for xhtml2pdf tanpa bikin SuspiciousFileOperation.
    """
    static_url = getattr(settings, "STATIC_URL", "/static/")

    # 1) kalau diawali STATIC_URL → resolve manual ke BASE_DIR/static
    if uri.startswith(static_url):
        subpath = uri[len(static_url):]
        candidate = os.path.join(settings.BASE_DIR, "static", subpath)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    # 2) coba lewat finders (fallback, misalnya static di app)
    result = finders.find(uri)
    if result:
        if isinstance(result, (list, tuple)):
            result = result[0]
        return os.path.abspath(result)

    # 3) kalau absolute path sudah valid
    if os.path.isabs(uri) and os.path.isfile(uri):
        return os.path.abspath(uri)

    # 4) fallback: biarin pisa coba handle
    return uri





def quotation_pdf(request, pk):
    q = get_object_or_404(
        SalesQuotation.objects.select_related("customer", "currency")
        .prefetch_related("lines__origin", "lines__destination", "lines__uom"),
        pk=pk
    )
    # render template PDF khusus
    html = render_to_string("freight/quotation_pdf.html", {"q": q, "is_pdf": True})

    buf = io.BytesIO()
    pdf = pisa.CreatePDF(io.BytesIO(html.encode("utf-8")),
                         dest=buf, encoding="utf-8",
                         link_callback=_link_callback)
    if pdf.err:
        return HttpResponse("Gagal membuat PDF.", status=500)

    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename=\"Quotation-{q.number}.pdf\"'
    return resp


def order_print(request, pk):
    so = get_object_or_404(
        SalesOrder.objects.select_related("customer", "currency")
        .prefetch_related("lines__origin", "lines__destination", "lines__uom"),
        pk=pk
    )
    return render(request, "freight/order_print.html", {"o": so, "is_pdf": False})


def order_pdf(request, pk):
    so = get_object_or_404(
        SalesOrder.objects.select_related("customer", "currency")
        .prefetch_related("lines__origin", "lines__destination", "lines__uom"),
        pk=pk
    )
    html = render_to_string("freight/order_pdf.html", {"o": so, "is_pdf": True})

    buf = io.BytesIO()
    pdf = pisa.CreatePDF(
        io.BytesIO(html.encode("utf-8")),
        dest=buf,
        encoding="utf-8",
        link_callback=_link_callback,
    )
    if pdf.err:
        return HttpResponse("Gagal membuat PDF.", status=500)

    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="SO-{so.number}.pdf"'
    return resp
