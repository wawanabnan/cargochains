# partners/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.http import JsonResponse
from django.db.models import Q

from geo.models import Location
from .models import Partner
from .forms import PartnerForm
from django.shortcuts import get_object_or_404
from .models import Partner, PartnerRole  # pastikan PartnerRole di-import

# partners/views.py

from .models import Partner, PartnerRole, PartnerRoleTypes




class PartnerListView(LoginRequiredMixin, ListView):
    model = Partner
    template_name = "partners/list.html"
    context_object_name = "partners"
    paginate_by = 20

    def get_queryset(self):
        qs = Partner.objects.all().select_related("sales_user", "location")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(company_name__icontains=q)
                | Q(city__icontains=q)
            )
        return qs.order_by("name")

class PartnerCreateView(CreateView):
    model = Partner
    form_class = PartnerForm
    template_name = "partners/form.html"
    success_url = reverse_lazy("partners:partner_list")

    def form_invalid(self, form):
        print("=== PartnerCreateView INVALID ===")
        print(form.errors.as_json())
        return super().form_invalid(form)


class PartnerUpdateView(UpdateView):
    model = Partner
    form_class = PartnerForm
    template_name = "partners/form.html"
    success_url = reverse_lazy("partners:partner_list")

    def form_invalid(self, form):
        print("=== PartnerUpdateView INVALID ===")
        print(form.errors.as_json())
        return super().form_invalid(form)
    

class PartnerDeleteView(LoginRequiredMixin, DeleteView):
    model = Partner
    template_name = "partners/confirm_delete.html"
    success_url = reverse_lazy("partners:partner_list")


# 🔎 Autocomplete lokasi pakai CBV (pakai geo.Location)
class LocationAutocompleteView(LoginRequiredMixin, View):
    """Return JSON for autocomplete fields (location)."""

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        if not q:
            return JsonResponse([], safe=False)

        qs = (
            Location.objects.filter(
                Q(name__icontains=q)
                | Q(parent__name__icontains=q)
                | Q(parent__parent__name__icontains=q)
            )
            .filter(kind__in=["village", "district", "regency", "province"])
            .select_related("parent", "parent__parent", "parent__parent__parent")
            .order_by("kind", "name")[:20]
        )

        data = []
        for obj in qs:
            parts = [obj.name]
            p = obj.parent
            while p:
                parts.append(p.name)
                p = p.parent
            label = " → ".join(reversed(parts))
            data.append(
                {
                    "id": obj.pk,
                    "name": obj.name,
                    "kind": getattr(obj, "kind", ""),
                    "label": label,
                }
            )
        return JsonResponse(data, safe=False)



class PartnerDetailJsonView(View):
    def get(self, request, pk):
        p = get_object_or_404(Partner, pk=pk)

        def loc_name(loc):
            return loc.name if loc else ""

        data = {
            "id": p.id,
            "name": p.name,
            "phone": p.phone or "",
            "mobile": p.mobile or "",
            "address_line1": p.address_line1 or "",
            "address_line2": p.address_line2 or "",
            "province": loc_name(getattr(p, "province", None)),
            "regency": loc_name(getattr(p, "regency", None)),
            "district": loc_name(getattr(p, "district", None)),
            "village": loc_name(getattr(p, "village", None)),
            "city": p.city or "",
            "country": p.country or "",
            "post_code": p.post_code or "",
        }
        return JsonResponse(data)
    




class PartnerAutocompleteView(View):
    """
    Autocomplete untuk Partner.
    - Default: hanya partner dengan role CUSTOMER
    - Param optional ?role= untuk role lain (misal vendor, carrier, dll).
    """
    limit = 20

    def get_queryset(self, q: str, role: str | None):
        qs = Partner.objects.all()

        # --- FILTER ROLE PAKAI PartnerRole LANGSUNG (AMAN) ---
        if role:
            partner_ids = (
                PartnerRole.objects
                .filter(role_type__code__iexact=role)
                .values_list("partner_id", flat=True)
            )
        else:
            # default: CUSTOMER
            partner_ids = (
                PartnerRole.objects
                .filter(role_type__code__iexact="customer")
                .values_list("partner_id", flat=True)
            )

        qs = qs.filter(id__in=partner_ids)

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(company_name__icontains=q)
            )

        return qs.select_related("province", "regency", "district", "village").distinct()[: self.limit]

    def normalize(self, p: Partner):
        parts = []
        if getattr(p, "address_line1", None):
            parts.append(p.address_line1)
        if getattr(p, "city", None):
            parts.append(p.city)
        if getattr(p, "province", None):
            parts.append(p.province.name)
        addr = ", ".join(parts)

        return {
            "id": p.id,
            "name": p.name,
            "company_name": p.company_name or "",
            "label": p.company_name or p.name,
            "value": p.company_name or p.name,
            "address": addr,
             "phone": p.phone or "",
            "mobile": p.mobile or "",
            "province_id": p.province_id,
            "regency_id": p.regency_id,
            "district_id": p.district_id,
            "village_id": p.village_id,

        }

    def get(self, request, *args, **kwargs):
        q = (request.GET.get("q") or "").strip()
        role = (request.GET.get("role") or "").strip() or None
        qs = self.get_queryset(q, role)
        data = [self.normalize(p) for p in qs]
        return JsonResponse(data, safe=False)



class PartnerAutocompleteView(View):
    """
    Autocomplete untuk Partner.
    - Default: hanya partner dengan role CUSTOMER
    - Param optional ?role= untuk role lain (misal vendor, carrier, dll).
    """
    limit = 20

    def get_queryset(self, q: str, role: str | None):
        qs = Partner.objects.all()

        # --- FILTER ROLE PAKAI PartnerRole LANGSUNG (AMAN) ---
        if role:
            partner_ids = (
                PartnerRole.objects
                .filter(role_type__code__iexact=role)
                .values_list("partner_id", flat=True)
            )
            
        else:
            # default: CUSTOMER
            partner_ids = (
                PartnerRole.objects
                .filter(role_type__code__iexact="customer")
                .values_list("partner_id", flat=True)
            )

        qs = qs.filter(id__in=partner_ids)

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(company_name__icontains=q)
            )

        return qs.select_related("province", "regency", "district", "village").distinct()[: self.limit]

    def normalize(self, p: Partner):
        parts = []
        if getattr(p, "address_line1", None):
            parts.append(p.address_line1)
        if getattr(p, "city", None):
            parts.append(p.city)
        if getattr(p, "province", None):
            parts.append(p.province.name)
        addr = ", ".join(parts)

        return {
            "id": p.id,
            "name": p.name,
            "company_name": p.company_name or "",
            "label": p.company_name or p.name,
            "value": p.company_name or p.name,
            "address": addr,
             "phone": p.phone or "",
            "mobile": p.mobile or "",
            "province_id": p.province_id,
            "regency_id": p.regency_id,
            "district_id": p.district_id,
            "village_id": p.village_id,

        }

    def get(self, request, *args, **kwargs):
        q = (request.GET.get("q") or "").strip()
        role = (request.GET.get("role") or "").strip() or None
        qs = self.get_queryset(q, role)
        data = [self.normalize(p) for p in qs]
        return JsonResponse(data, safe=False)
