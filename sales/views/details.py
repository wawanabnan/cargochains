# sales/views/details.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from account.decorators import role_required
from ..models import SalesOrder, SalesQuotation
from ..auth import SalesAccessRequiredMixin


@method_decorator(login_required(login_url="account:login"), name="dispatch")
@method_decorator(role_required("sales", "admin"), name="dispatch")
class QuotationDetailView(LoginRequiredMixin, DetailView):
    model = SalesQuotation
    context_object_name = "quotation"
    template_name = "freight/quotation_details.html"   # ← sesuai yang kamu pakai
    pk_url_kwarg = "pk"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.object
        # isi ctx["lines"] supaya template lama tetap dapat item baris
        lines = None
        for accessor in ("lines", "quotation_lines", "items", "details"):
            mgr = getattr(q, accessor, None)
            if hasattr(mgr, "all"):
                lines = mgr.all(); break
        if lines is None:
            for rel in q._meta.related_objects:
                if rel.one_to_many and "line" in rel.related_model.__name__.lower():
                    mgr = getattr(q, rel.get_accessor_name())
                    if hasattr(mgr, "all"):
                        lines = mgr.all(); break
        ctx["lines"] = lines or []
        return ctx

@method_decorator(login_required(login_url="account:login"), name="dispatch")
@method_decorator(role_required("sales", "admin"), name="dispatch")
class OrderDetailView(LoginRequiredMixin, DetailView):
    model = SalesOrder
    context_object_name = "order"
    template_name = "freight/order_details.html"       # ← sesuai yang kamu pakai
    pk_url_kwarg = "pk"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        o = self.object
        lines = None
        for accessor in ("lines", "order_lines", "items", "details"):
            mgr = getattr(o, accessor, None)
            if hasattr(mgr, "all"):
                lines = mgr.all(); break
        if lines is None:
            for rel in o._meta.related_objects:
                if rel.one_to_many and "line" in rel.related_model.__name__.lower():
                    mgr = getattr(o, rel.get_accessor_name())
                    if hasattr(mgr, "all"):
                        lines = mgr.all(); break
        ctx["lines"] = lines or []
        return ctx
