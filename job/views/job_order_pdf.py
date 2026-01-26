from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

def test_weasyprint(request):
    rows = range(1, 300)  # stress test, ubah jumlahnya

    html = render_to_string(
        "print/test_weasy.html",
        {"rows": rows},          # ✅ isi context
        request=request
    )

    pdf = HTML(
        string=html,
        base_url=request.build_absolute_uri("/")  # ✅ biar /static kebaca
    ).write_pdf()

    return HttpResponse(pdf, content_type="application/pdf")
