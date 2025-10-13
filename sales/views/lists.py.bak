# sales/views/lists.py
from django.db.models import Q,Count
from django.views.generic import ListView
from ..models import SalesQuotation, SalesOrder, Partner,SalesService
from ..auth import SalesAccessRequiredMixin, sales_queryset_for_user, is_sales_supervisor
from sales.utils.search import parse_date, parse_multi, parse_bool, safe_int

from datetime import datetime
from  sales.querysets import sales_queryset_for_user
from sales.mixins import SalesAccessRequiredMixin  # asumsi ka
from django.contrib.auth.models import User

class QuotationListView(SalesAccessRequiredMixin, ListView):
    model = SalesQuotation
    template_name = "freight/quotation_list.html"
    context_object_name = "quotations"
    paginate_by = 25
    ordering = ["-created_at"]  # atau ["-id"] bila perlu

    # ---------- helpers mini (biar tidak perlu utils.py) ----------
    @staticmethod
    def _none_if_empty(s):
        return s if (s and str(s).strip()) else None

    @staticmethod
    def _parse_bool(s):
        return str(s).lower() in {"1", "true", "yes", "on"}

    @classmethod
    def _parse_date(cls, s):
        s = cls._none_if_empty(s)
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_multi(req, key):
        vals = req.GET.getlist(key)
        if vals:
            return [v for v in vals if v]
        raw = req.GET.get(key)
        if not raw:
            return []
        return [v.strip() for v in raw.split(",") if v.strip()]

    @staticmethod
    def _safe_int(s):
        try:
            return int(s)
        except (TypeError, ValueError):
            return None

    # ---------- queryset builder ----------
    def get_queryset(self):
        req = self.request
        qtext      = (req.GET.get("q") or "").strip()
        states     = self._parse_multi(req, "state")  # ?state=draft&state=sent atau ?state=draft,sent
        cust_id    = self._safe_int(req.GET.get("customer"))
        user_id    = self._safe_int(req.GET.get("sales_user"))
        svc_id     = self._safe_int(req.GET.get("service"))
        my_only    = self._parse_bool(req.GET.get("my"))
        d_from     = self._parse_date(req.GET.get("date_from"))
        d_to       = self._parse_date(req.GET.get("date_to"))
        sort_key   = (req.GET.get("sort") or "").strip()
        direction  = (req.GET.get("dir") or "desc").lower()

        qs = (SalesQuotation.objects
              .select_related("customer", "sales_agency", "sales_user",
                              "currency", "payment_term", "sales_service"))

        # Quick search (multi kolom)
        if qtext:
            qs = qs.filter(
                Q(number__icontains=qtext) |
                Q(status__icontains=qtext) |
                Q(customer__name__icontains=qtext) |
                Q(sales_user__username__icontains=qtext) |
                Q(sales_user__first_name__icontains=qtext) |
                Q(sales_user__last_name__icontains=qtext) |
                Q(sales_service__name__icontains=qtext)
            )

        # Filter dinamis
        if states:
            qs = qs.filter(status__in=states)
        if cust_id:
            qs = qs.filter(customer_id=cust_id)
        if user_id:
            qs = qs.filter(sales_user_id=user_id)
        if svc_id:
            qs = qs.filter(sales_service_id=svc_id)
        if my_only and req.user.is_authenticated:
            qs = qs.filter(sales_user_id=req.user.id)
        if d_from:
            qs = qs.filter(date__gte=d_from)
        if d_to:
            qs = qs.filter(date__lte=d_to)

        # Batasi akses object-level
        qs = sales_queryset_for_user(qs, req.user)

        # Sorting
        # map “frontend sort” → kolom DB
        sort_map = {
            "id": "id",
            "created_at": "created_at",
            "number": "number",
            "status": "status",
            "sales_user": "sales_user__username",
            "date": "date",
            "customer": "customer__name",
        }
        if sort_key in sort_map:
            field = sort_map[sort_key]
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + field)
        elif getattr(self, "ordering", None):
            qs = qs.order_by(*self.ordering)

        return qs

    # ---------- context tambahan (dropdowns, facets, querystring) ----------
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req = self.request

        # Facets ringan per status (untuk panel kiri)
        ctx["facets"] = (SalesQuotation.objects
                         .values("status")
                         .annotate(total=Count("id"))
                         .order_by("status"))

        # Data dropdown (batasi biar ringan)
        ctx["customers"] = Partner.objects.only("id", "name").order_by("name")[:500]
        ctx["users"]     = User.objects.only("id", "username", "first_name", "last_name").order_by("first_name", "username")[:500]
        ctx["services"]  = SalesService.objects.only("id", "name").order_by("name")[:500]
        ctx["status_list"] = ["DRAFT", "SENT", "ACCEPTED", "ORDERED", "CANCELLED"]


        # Echo GET params ke template
        ctx.update({
            "title": "Freight Quotations",
            "ns": "sales",
            "menu": "quotation",
            "q": req.GET.get("q", ""),
            "states": self._parse_multi(req, "state"),
            "my_only": self._parse_bool(req.GET.get("my")),
            "d_from": self._parse_date(req.GET.get("date_from")),
            "d_to": self._parse_date(req.GET.get("date_to")),
            "sort": req.GET.get("sort", ""),
            "dir": (req.GET.get("dir") or "desc").lower(),
            "selected_customer": req.GET.get("customer", ""),
            "selected_user": req.GET.get("sales_user", ""),
            "selected_service": req.GET.get("service", ""),
        })

        # Querystring tanpa 'page' agar pagination maintain filter
        qs_items = [(k, v) for k, v in req.GET.items() if k != "page"]
        ctx["current_query"] = "&".join(f"{k}={v}" for k, v in qs_items)

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
        
