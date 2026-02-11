from decimal import Decimal
from django.views.generic import DetailView
from work_orders.models.vendor_bookings import VendorBooking
from sales.models import SalesConfig


class VendorBookingPrintView(DetailView):
    model = VendorBooking
    template_name = "service_orders/print/vb_preview.html"
    context_object_name = "vb"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        vb = (
            VendorBooking.objects
            .select_related(
                "job_order",
                "vendor",
                "payment_term",
                "created_by",
            )
            .prefetch_related("lines__taxes", "lines__uom", "lines__cost_type")
            .get(pk=ctx["vb"].pk)
        )

        lines = vb.lines.all().order_by("id")

        subtotal = sum((ln.amount or Decimal("0")) for ln in lines)
        tax_ppn = vb.ppn_amount
        tax_pph = vb.pph_amount
        total = subtotal + tax_ppn - tax_pph - (vb.discount_amount or Decimal("0"))

        # -----------------------------
        # Signature context (same pattern as quotation)
        # -----------------------------
        cfg = SalesConfig.get_solo()
        src = (getattr(cfg, "service_order_signature_source", "") or "").upper()

        signer = None
        if src == "SPECIFIC_USER":
            signer = getattr(cfg, "service_order_signature_user", None)
        else:
            # SALES_USER
            signer = vb.created_by

        profile = getattr(signer, "profile", None) if signer else None

        ctx.update({
            "vb": vb,
            "lines": lines,
            "subtotal": subtotal,
            "tax_ppn": tax_ppn,
            "tax_pph": tax_pph,
            "total": total,

            # keep names aligned with quotation template style
            "signature_name": (signer.get_full_name() or signer.username) if signer else "",
            "signature_title": getattr(profile, "title", "") if profile else "",
            "signature_image": getattr(profile, "signature", None) if profile else None,
        })
        return ctx
