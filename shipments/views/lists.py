# shipments/views/lists.py
from datetime import datetime
from urllib.parse import urlencode
from django.db.models import Q
from django.views.generic import ListView
from ..models import Shipment

def _parse_date(s: str):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def _count_selected_filters(request):
    n = 0
    n += len([s for s in request.GET.getlist("status") if s.strip()])
    n += len([c for c in request.GET.getlist("customer") if c.isdigit()])
    n += len([s for s in request.GET.getlist("service") if s.isdigit()])
    if (request.GET.get("etd_start") or "").strip(): n += 1
    if (request.GET.get("etd_end") or "").strip():   n += 1
    if (request.GET.get("eta_start") or "").strip(): n += 1
    if (request.GET.get("eta_end") or "").strip():   n += 1
    return n

class ShipmentListView(ListView):
    model = Shipment
    template_name = "shipments/shipment_list.html"
    context_object_name = "shipments"
    paginate_by = 10
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            Shipment.objects
            .select_related("customer", "sales_service", "origin", "destination")
        )

        # --- search ---
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(number__icontains=q) |
                Q(booking_number__icontains=q) |
                Q(vessel_name__icontains=q) |       # ← pakai vessel_name (bukan vessel__name)
                Q(voyage_no__icontains=q) |
                Q(customer__name__icontains=q) |
                Q(origin__name__icontains=q) |
                Q(destination__name__icontains=q)
            )

        # --- sorting ---
        sort = (self.request.GET.get("sort") or "").strip()
        direction = (self.request.GET.get("dir") or "desc").lower()
        sort_map = {
            "number": "number",
            "created_at": "created_at",
            "status": "status",
            "customer": "customer__name",
            "service": "sales_service__name",
            "etd": "etd",
            "eta": "eta",
        }
        if sort in sort_map:
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + sort_map[sort])
        else:
            qs = qs.order_by("-created_at")

        # --- filters ---
        flt_statuses = [s.strip() for s in self.request.GET.getlist("status") if s.strip()]
        flt_customers = [int(x) for x in self.request.GET.getlist("customer") if x.isdigit()]
        flt_services  = [int(x) for x in self.request.GET.getlist("service") if x.isdigit()]

        if flt_statuses:
            qs = qs.filter(status__in=flt_statuses)
        if flt_customers:
            qs = qs.filter(customer_id__in=flt_customers)
        if flt_services:
            qs = qs.filter(sales_service_id__in=flt_services)

        # ETD / ETA range (field kamu ada: etd, eta)
        etd_start = _parse_date(self.request.GET.get("etd_start"))
        etd_end   = _parse_date(self.request.GET.get("etd_end"))
        eta_start = _parse_date(self.request.GET.get("eta_start"))
        eta_end   = _parse_date(self.request.GET.get("eta_end"))

        if etd_start:
            qs = qs.filter(etd__date__gte=etd_start) if hasattr(Shipment._meta.get_field("etd"), "attname") and Shipment._meta.get_field("etd").get_internal_type()=="DateTimeField" else qs.filter(etd__gte=etd_start)
        if etd_end:
            qs = qs.filter(etd__date__lte=etd_end)   if Shipment._meta.get_field("etd").get_internal_type()=="DateTimeField" else qs.filter(etd__lte=etd_end)
        if eta_start:
            qs = qs.filter(eta__date__gte=eta_start) if Shipment._meta.get_field("eta").get_internal_type()=="DateTimeField" else qs.filter(eta__gte=eta_start)
        if eta_end:
            qs = qs.filter(eta__date__lte=eta_end)   if Shipment._meta.get_field("eta").get_internal_type()=="DateTimeField" else qs.filter(eta__lte=eta_end)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        qs = self.request.GET.copy()
        qs.pop("page", None)
        base_qs = urlencode(qs, doseq=True)

        status_choices = list(getattr(Shipment, "STATUS_CHOICES", []))

        CustomerModel = Shipment._meta.get_field("customer").remote_field.model
        ServiceModel  = Shipment._meta.get_field("sales_service").remote_field.model

        # Hanya partner yang ber-role "Customer"
        customers = (
            CustomerModel.objects
            .filter(partner_roles__role_type__code__iexact="CUSTOMER")  # atau __name__iexact="Customer"
            .distinct().order_by("name" if hasattr(CustomerModel, "name") else "id")
        )
        services  = list(ServiceModel.objects.all().order_by("name" if hasattr(ServiceModel, "name") else "id"))

        flt_statuses = [s.strip() for s in self.request.GET.getlist("status") if s.strip()]
        flt_customers = [int(x) for x in self.request.GET.getlist("customer") if x.isdigit()]
        flt_services  = [int(x) for x in self.request.GET.getlist("service") if x.isdigit()]

        ctx.update({
            "q": self.request.GET.get("q", ""),
            "sort": self.request.GET.get("sort", ""),
            "dir": self.request.GET.get("dir", "desc"),
            "base_qs": base_qs,

            "status_choices": status_choices,
            "customers": customers,
            "services": services,

            "flt_statuses": flt_statuses,
            "flt_customers": flt_customers,
            "flt_services": flt_services,

            "etd_start": self.request.GET.get("etd_start", ""),
            "etd_end": self.request.GET.get("etd_end", ""),
            "eta_start": self.request.GET.get("eta_start", ""),
            "eta_end": self.request.GET.get("eta_end", ""),

            "filters_count": _count_selected_filters(self.request),  # ← untuk badge di tombol
        })
        return ctx