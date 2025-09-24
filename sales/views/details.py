# sales/views/details.py
from django.views.generic import DetailView
from ..models import SalesQuotation, SalesOrder
from ..auth import SalesAccessRequiredMixin, sales_queryset_for_user

class QuotationDetailView(SalesAccessRequiredMixin, DetailView):
    model = SalesQuotation
    template_name = "freight/quotation_details.html"
    context_object_name = "quotation"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        qs = (SalesQuotation.objects
              .select_related("customer", "sales_user")
              .prefetch_related("lines"))
        return sales_queryset_for_user(qs, self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lines"] = self.object.lines.all()  # kompatibel dgn template lama
        return ctx

class OrderDetailView(SalesAccessRequiredMixin, DetailView):
    model = SalesOrder
    template_name = "freight/order_details.html"
    context_object_name = "order"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        qs = (SalesOrder.objects
              .select_related("customer", "sales_user", "sales_quotation")
              .prefetch_related("lines"))
        return sales_queryset_for_user(qs, self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lines"] = self.object.lines.all()
        return ctx
