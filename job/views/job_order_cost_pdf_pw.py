import os
import tempfile
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

from playwright.sync_api import sync_playwright


@login_required
def joborder_cost_pdf(request, pk):
    # ctx kamu sudah punya dari logic sebelumnya
    # contoh:
    # job = get_object_or_404(JobOrder, pk=pk)
    # ctx = build_context_for_print(job)


    ctx = ...  # <-- pakai ctx yang sama dengan preview

    html = render_to_string("job_order/print_cost_preview.html", ctx, request=request)

    # base_url penting agar {% static %} jadi absolute & bisa diload
    base_url = request.build_absolute_uri("/")  # mis. http://127.0.0.1:8000/

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # set_content + base_url supaya relative URL resolve
        page.set_content(html, wait_until="networkidle", base_url=base_url)

        pdf_bytes = page.pdf(
            format="A4",
            margin={"top": "12mm", "right": "12mm", "bottom": "14mm", "left": "12mm"},
            print_background=True,   # penting biar th background #f2f2f2 ikut
            prefer_css_page_size=True,  # kalau kamu pakai @page di CSS
        )

        browser.close()

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="job-cost.pdf"'
    return resp
