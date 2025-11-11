# sales/views/lists.py
from django.db.models import Q
from django.views.generic import ListView
from urllib.parse import urlencode

from ..models import SalesQuotation, SalesOrder
from ..auth import (
    SalesAccessRequiredMixin,
    sales_queryset_for_user,
    is_sales_supervisor,
)


class FreightQuotationListView(SalesAccessRequiredMixin, ListView):
    model = SalesQuotation
    template_name = "freight/quotation_list.html"
    context_object_name = "quotations"
    paginate_by = 10
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            SalesQuotation.objects
            .select_related(
                "customer", "sales_user",
                "currency", "sales_service", "sales_agency", "payment_term"
            )
        )

        # --- search ---
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

        # --- sorting (opsional, kalau kamu sudah punya bagian ini, boleh biarkan) ---
        sort = (self.request.GET.get("sort") or "").strip()
        direction = (self.request.GET.get("dir") or "desc").lower()
        allowed = {"number", "created_at", "status", "id", "sales_user"}
        if sort in allowed:
            sort_key = "sales_user__username" if sort == "sales_user" else sort
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + sort_key)
        else:
            qs = qs.order_by("-created_at")

        # --- filters ---
        flt_statuses     = [s.strip() for s in self.request.GET.getlist("status") if s.strip()]
        flt_currencies   = [int(x) for x in self.request.GET.getlist("currency") if x.isdigit()]
        flt_services     = [int(x) for x in self.request.GET.getlist("service") if x.isdigit()]
        flt_agents       = [int(x) for x in self.request.GET.getlist("agent") if x.isdigit()]
        flt_paymentterms = [int(x) for x in self.request.GET.getlist("payment_term") if x.isdigit()]

        if flt_statuses:
            qs = qs.filter(status__in=flt_statuses)
        if flt_currencies:
            qs = qs.filter(currency_id__in=flt_currencies)
        if flt_services:
            qs = qs.filter(sales_service_id__in=flt_services)
        if flt_agents:
            qs = qs.filter(sales_agency_id__in=flt_agents)  # ← FK ke Partner (Agency)
        if flt_paymentterms:
            qs = qs.filter(payment_term_id__in=flt_paymentterms)

        qs = sales_queryset_for_user(qs, self.request.user)
        return qs

        
    def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)

            # Buat base_qs agar pagination tidak menduplikasi parameter
            qs = self.request.GET.copy()
            qs.pop("page", None)
            base_qs = urlencode(qs, doseq=True)

            page_obj     = ctx.get("page_obj") or ctx.get("quotations")
            paginator    = ctx.get("paginator") or (page_obj and page_obj.paginator)
            is_paginated = ctx.get("is_paginated", bool(page_obj and page_obj.has_other_pages()))

            # Ambil choices status
            status_choices = list(SalesQuotation._meta.get_field("status").choices)

            # Ambil model dari field FK di SalesQuotation
            CurrencyModel    = SalesQuotation._meta.get_field("currency").remote_field.model
            ServiceModel     = SalesQuotation._meta.get_field("sales_service").remote_field.model
            AgencyModel      = SalesQuotation._meta.get_field("sales_agency").remote_field.model
            PaymentTermModel = SalesQuotation._meta.get_field("payment_term").remote_field.model

            currencies   = list(CurrencyModel.objects.all().order_by("id"))
            services     = list(ServiceModel.objects.all().order_by("id"))
            paymentterms = list(PaymentTermModel.objects.all().order_by("id"))

            # === ✅ Ambil hanya Partner yang punya role agency ===
            agents = list(
                AgencyModel.objects.filter(
                    Q(partner_roles__role_type__code__iexact="agency") |
                    Q(partner_roles__role_type__name__iexact="agency")
                ).distinct().order_by("name")
            )

            # nilai terpilih untuk preselect di template
            flt_statuses     = [s.strip() for s in self.request.GET.getlist("status") if s.strip()]
            flt_currencies   = [int(x) for x in self.request.GET.getlist("currency") if x.isdigit()]
            flt_services     = [int(x) for x in self.request.GET.getlist("service") if x.isdigit()]
            flt_agents       = [int(x) for x in self.request.GET.getlist("agent") if x.isdigit()]
            flt_paymentterms = [int(x) for x in self.request.GET.getlist("payment_term") if x.isdigit()]

            ctx.update({
                "title": "Freight Quotations",
                "ns": "sales",
                "menu": "quotation",
                "q": self.request.GET.get("q", ""),
                "sort": self.request.GET.get("sort", ""),
                "dir": self.request.GET.get("dir", "desc"),
                "sp": self.request.GET.get("sp", ""),

                "base_qs": base_qs,
                "page_obj": page_obj,
                "paginator": paginator,
                "is_paginated": is_paginated,

                # data dropdown
                "status_choices": status_choices,
                "currencies": currencies,
                "services": services,
                "agents": agents,           # ← hanya Partner ber-role “agency”
                "paymentterms": paymentterms,

                # nilai terpilih
                "flt_statuses": flt_statuses,
                "flt_currencies": flt_currencies,
                "flt_services": flt_services,
                "flt_agents": flt_agents,
                "flt_paymentterms": flt_paymentterms,
            })
            return ctx

   
# =====================
# FREIGHT ORDERS LIST
# =====================
# sales/views/lists.py

class FreightOrderListView(SalesAccessRequiredMixin, ListView):
    model = SalesOrder
    template_name = "freight/order_list.html"
    context_object_name = "orders"
    paginate_by = 10
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            SalesOrder.objects
            .select_related(
                "sales_quotation", "customer", "sales_user",
                "currency", "sales_service", "sales_agency", "payment_term"
            )
        )

        # --- search ---
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(status__icontains=q)
                | Q(customer__name__icontains=q)
                | Q(sales_quotation__number__icontains=q)
            )

        # --- sorting ---
        sort = (self.request.GET.get("sort") or "").strip()
        direction = (self.request.GET.get("dir") or "desc").lower()
        allowed = {"number", "created_at", "status", "sales_quotation__number"}
        if sort in allowed:
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + sort)
        else:
            qs = qs.order_by("-created_at")

        # --- filters ---
        flt_statuses     = [s.strip() for s in self.request.GET.getlist("status") if s.strip()]
        flt_currencies   = [int(x) for x in self.request.GET.getlist("currency") if x.isdigit()]
        flt_services     = [int(x) for x in self.request.GET.getlist("service") if x.isdigit()]
        flt_agents       = [int(x) for x in self.request.GET.getlist("agent") if x.isdigit()]
        flt_paymentterms = [int(x) for x in self.request.GET.getlist("payment_term") if x.isdigit()]

        if flt_statuses:
            qs = qs.filter(status__in=flt_statuses)
        if flt_currencies:
            qs = qs.filter(currency_id__in=flt_currencies)
        if flt_services:
            qs = qs.filter(sales_service_id__in=flt_services)
        if flt_agents:
            qs = qs.filter(sales_agency_id__in=flt_agents)
        if flt_paymentterms:
            qs = qs.filter(payment_term_id__in=flt_paymentterms)

        qs = sales_queryset_for_user(qs, self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # base_qs untuk pagination
        qs = self.request.GET.copy()
        qs.pop("page", None)
        base_qs = urlencode(qs, doseq=True)

        page_obj     = ctx.get("page_obj") or ctx.get("orders")
        paginator    = ctx.get("paginator") or (page_obj and page_obj.paginator)
        is_paginated = ctx.get("is_paginated", bool(page_obj and page_obj.has_other_pages()))

        # === ambil data untuk dropdown ===
        status_choices = list(SalesOrder._meta.get_field("status").choices)

        CurrencyModel    = SalesOrder._meta.get_field("currency").remote_field.model
        ServiceModel     = SalesOrder._meta.get_field("sales_service").remote_field.model
        AgencyModel      = SalesOrder._meta.get_field("sales_agency").remote_field.model
        PaymentTermModel = SalesOrder._meta.get_field("payment_term").remote_field.model

        currencies   = list(CurrencyModel.objects.all().order_by("id"))
        services     = list(ServiceModel.objects.all().order_by("id"))
        paymentterms = list(PaymentTermModel.objects.all().order_by("id"))

        # === ambil partner ber-role agency ===
        agents = list(
            AgencyModel.objects.filter(
                Q(partner_roles__role_type__code__iexact="agency") |
                Q(partner_roles__role_type__name__iexact="agency")
            ).distinct().order_by("name")
        )

        # nilai terpilih
        flt_statuses     = [s.strip() for s in self.request.GET.getlist("status") if s.strip()]
        flt_currencies   = [int(x) for x in self.request.GET.getlist("currency") if x.isdigit()]
        flt_services     = [int(x) for x in self.request.GET.getlist("service") if x.isdigit()]
        flt_agents       = [int(x) for x in self.request.GET.getlist("agent") if x.isdigit()]
        flt_paymentterms = [int(x) for x in self.request.GET.getlist("payment_term") if x.isdigit()]

        ctx.update({
            "title": "Freight Orders",
            "ns": "sales",
            "menu": "order",
            "q": self.request.GET.get("q", ""),
            "sort": self.request.GET.get("sort", ""),
            "dir": self.request.GET.get("dir", "desc"),

            "base_qs": base_qs,
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": is_paginated,

            # dropdown data
            "status_choices": status_choices,
            "currencies": currencies,
            "services": services,
            "agents": agents,
            "paymentterms": paymentterms,

            # selected filters
            "flt_statuses": flt_statuses,
            "flt_currencies": flt_currencies,
            "flt_services": flt_services,
            "flt_agents": flt_agents,
            "flt_paymentterms": flt_paymentterms,
        })
        return ctx
