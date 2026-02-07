from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import DetailView

from weasyprint import HTML

from job.models.job_orders import JobOrder  # sesuaikan path model kamu
from job.services.print_context import job_order_print_context


def add_signature_ctx(ctx, user):
    profile = getattr(user, "profile", None)
    ctx.setdefault("signature_name", (user.get_full_name() or user.username))
    ctx.setdefault("signature_title", getattr(profile, "title", "") if profile else "")
    ctx.setdefault("signature_image", getattr(profile, "signature", None) if profile else None)
    return ctx


class JobOrderPrintPreviewView(LoginRequiredMixin, DetailView):
    model = JobOrder
    template_name = "job_order/job_order_preview.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(job_order_print_context(self.object))
        add_signature_ctx(ctx, self.request.user)
        return ctx


class JobOrderPDFView(LoginRequiredMixin, View):
    def get(self, request, pk: int, *args, **kwargs):
        jo = get_object_or_404(JobOrder, pk=pk)

        ctx = job_order_print_context(jo) or {}

        # anti kosong (samakan pattern quotation)
        ctx.setdefault("job_order", jo)
        ctx.setdefault("jo", jo)

        add_signature_ctx(ctx, request.user)

        html = render_to_string("job_order/job_order_pdf.html", ctx, request=request)

        base_url = request.build_absolute_uri("/")
        pdf_bytes = HTML(string=html, base_url=base_url).write_pdf()

        filename = f"job-order-{(getattr(jo, 'job_number', None) or str(pk)).replace('/', '-')}.pdf"
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        return resp
