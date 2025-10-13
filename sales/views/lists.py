# sales/views/lists.py
from django.db.models import Q
from django.views.generic import ListView
from ..models import SalesQuotation, SalesOrder
from ..auth import SalesAccessRequiredMixin, sales_queryset_for_user, is_sales_supervisor
from sales.utils.search import parse_date, parse_multi, parse_bool, safe_int

class QuotationListView(SalesAccessRequiredMixin, ListView):
    model = SalesQuotation
    model = SalesQuotation
    template_name = "freight/quotation_list.html"
    context_object_name = "quotations"
    paginate_by = 25
    ordering = ["-created_at"]  # ganti ke ["-id"] jika tidak ada created_at

    def get_queryset(self):
        qs = SalesQuotation.objects.select_related("customer", "sales_user")
        if getattr(self, "ordering", None):
            qs = qs.order_by(*self.ordering)

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(status__icontains=q)
                | Q(customer__name__icontains=q)
                | Q(sales_user__username__icontains=q)
                | Q(sales_user__first_name__icontains=q)
                | Q(sales_user__last_name__icontains=q)
            )

        sp = (self.request.GET.get("sp") or "").strip()
        if sp and is_sales_supervisor(self.request.user):
            if sp == "me":
                qs = qs.filter(sales_user=self.request.user)
            elif sp.isdigit():
                qs = qs.filter(sales_user_id=int(sp))
            else:
                qs = qs.filter(
                    Q(sales_user__username__icontains=sp)
                    | Q(sales_user__first_name__icontains=sp)
                    | Q(sales_user__last_name__icontains=sp)
                )

        sort = (self.request.GET.get("sort") or "").strip()
        direction = (self.request.GET.get("dir") or "desc").lower()
        allowed = {"number", "created_at", "status", "id", "sales_user"}
        if sort in allowed:
            sort_key = "sales_user__username" if sort == "sales_user" else sort
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + sort_key)

        qs = sales_queryset_for_user(qs, self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "Freight Quotations",
            "ns": "sales",
            "menu": "quotation",
            "q": self.request.GET.get("q", ""),
            "sort": self.request.GET.get("sort", ""),
            "dir": self.request.GET.get("dir", "desc"),
            "sp": self.request.GET.get("sp", ""),
        })
        return ctx


# sales/views/lists.py
from django.db.models import Q
from django.views.generic import ListView
from ..auth import SalesAccessRequiredMixin, sales_queryset_for_user
from ..models import SalesOrder

class OrderListView(SalesAccessRequiredMixin, ListView):
    model = SalesOrder
    template_name = "freight/order_list.html"
    context_object_name = "orders"
    paginate_by = 25
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = sales_queryset_for_user(super().get_queryset(), self.request.user, include_null=True)

        # search
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(number__icontains=q) |
                Q(status__icontains=q) |
                Q(customer__name__icontains=q) |
                Q(sales_quotation__number__icontains=q)
            )

        # filters
        statuses = [s.strip() for s in self.request.GET.getlist("status") if s.strip()]
        if statuses:
            cond = Q()
            for s in statuses:
                cond |= Q(status__iexact=s)
            qs = qs.filter(cond)

        start = (self.request.GET.get("start") or "").strip()
        end   = (self.request.GET.get("end") or "").strip()
        if start:
            qs = qs.filter(created_at__date__gte=start)
        if end:
            qs = qs.filter(created_at__date__lte=end)

        if (self.request.GET.get("mine") or "") == "1":
            qs = qs.filter(sales_user=self.request.user)

        # sorting
        sort = (self.request.GET.get("sort") or "").strip()
        direction = (self.request.GET.get("dir") or "desc").lower()
        allowed = {"number", "created_at", "status", "sales_quotation__number"}
        if sort in allowed:
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + sort)
        else:
            qs = qs.order_by("-created_at")

        return qs.select_related(
            "sales_quotation", "customer", "sales_user", "sales_service",
            "currency", "payment_term", "sales_agency"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "q": self.request.GET.get("q", ""),
            "sort": self.request.GET.get("sort", ""),
            "dir": self.request.GET.get("dir", "desc"),
            "flt_statuses": [s.strip() for s in self.request.GET.getlist("status") if s.strip()],
            "flt_start": self.request.GET.get("start", ""),
            "flt_end": self.request.GET.get("end", ""),
            "flt_mine": (self.request.GET.get("mine") or "") == "1",
            # ↓ kirim list ke template, jadi TIDAK perlu filter |split
            "status_options": ["draft", "open", "confirmed", "processed", "in progress", "done", "canceled"],
        })
        return ctx
        
