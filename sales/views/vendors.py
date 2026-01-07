# sales/views/vendors.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404, render
from django.views import View
from django.contrib import messages

from partners.models import Partner, PartnerRole, PartnerRoleTypes
from sales.forms.vendors import VendorForm
from sales.forms.customer_contacts import CustomerContactForm  # reuse


class EntityContextMixin:
    entity_label = ""
    entity_urls = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["entity_label"] = self.entity_label
        ctx["entity_urls"] = self.entity_urls
        return ctx


class VendorQuerysetMixin:
    def get_queryset(self):
        # ✅ kalau Partner sudah punya Vendor manager, pakai itu
        mgr = getattr(Partner, "vendors", None)
        if mgr is not None:
            return mgr.all()

        # fallback: based on role
        vendor_ids = PartnerRole.objects.filter(
            role_type__code__iexact="vendor"
        ).values_list("partner_id", flat=True)
        return Partner.objects.filter(id__in=vendor_ids).distinct()


class VendorListView(LoginRequiredMixin, EntityContextMixin, VendorQuerysetMixin, ListView):
    model = Partner
    template_name = "customers/list.html"     # reuse
    context_object_name = "customers"         # reuse var existing
    paginate_by = 20

    entity_label = "Vendor"
    entity_urls = "vendor"

    def get_queryset(self):
        qs = super().get_queryset().select_related("province", "regency", "district", "village")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(company_name__icontains=q) |
                Q(phone__icontains=q)
            )
        return qs.order_by("name")


class VendorCreateView(LoginRequiredMixin, EntityContextMixin, CreateView):
    model = Partner
    form_class = VendorForm
    template_name = "customers/form.html"     # reuse

    entity_label = "Vendor"
    entity_urls = "vendor"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.company = None

        if obj.is_individual:
            obj.is_sales_contact = True
            obj.is_billing_contact = True
            obj.company_name = obj.company_name or ""
        else:
            if obj.company_name and not obj.name:
                obj.name = obj.company_name
            obj.is_sales_contact = False
            obj.is_billing_contact = False

        obj.save()

        role_vendor = PartnerRoleTypes.objects.get(code__iexact="vendor")
        PartnerRole.objects.get_or_create(partner=obj, role_type=role_vendor)

        messages.success(self.request, "Vendor berhasil dibuat.")
        return redirect(reverse("sales:vendor_detail", args=[obj.pk]))


class VendorUpdateView(LoginRequiredMixin, EntityContextMixin, VendorQuerysetMixin, UpdateView):
    model = Partner
    form_class = VendorForm
    template_name = "customers/form.html"     # reuse
    success_url = reverse_lazy("sales:vendor_list")

    entity_label = "Vendor"
    entity_urls = "vendor"


class VendorDetailView(LoginRequiredMixin, EntityContextMixin, VendorQuerysetMixin, DetailView):
    model = Partner
    template_name = "customers/detail.html"   # reuse
    context_object_name = "customer"          # reuse var existing

    entity_label = "Vendor"
    entity_urls = "vendor"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vendor = self.object

        ctx["contacts"] = vendor.contacts.all().order_by("id")
        ctx["contact_form"] = ctx.get("contact_form") or CustomerContactForm()

        open_flag = (self.request.GET.get("open_contact") or "").strip()
        ctx["open_contact"] = bool(open_flag) and open_flag not in ("0", "false", "False", "no", "NO")
        return ctx


class VendorDeleteView(LoginRequiredMixin, EntityContextMixin, VendorQuerysetMixin, DeleteView):
    model = Partner
    template_name = "customers/confirm_delete.html"  # reuse
    success_url = reverse_lazy("sales:vendor_list")

    entity_label = "Vendor"
    entity_urls = "vendor"


class VendorContactCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        vendor = get_object_or_404(Partner, pk=pk)

        form = CustomerContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.is_individual = True
            contact.company = vendor
            contact.save()

            messages.success(request, "Contact berhasil ditambahkan.")
            return redirect(reverse("sales:vendor_detail", args=[vendor.pk]))

        messages.error(request, f"Gagal menambah contact: {form.errors.as_text()}")
        return redirect(reverse("sales:vendor_detail", args=[vendor.pk]) + "?open_contact=1")


class VendorContactUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        contact = get_object_or_404(Partner, pk=pk, is_individual=True)
        vendor = contact.company

        form = CustomerContactForm(request.POST, instance=contact)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.is_individual = True
            obj.company = vendor
            obj.save()
            messages.success(request, "Contact berhasil diupdate.")
            return redirect(reverse("sales:vendor_detail", args=[vendor.pk]))

        contacts = vendor.contacts.all().order_by("id")
        return render(request, "customers/detail.html", {
            "customer": vendor,
            "contacts": contacts,
            "contact_form": form,
            "open_contact": True,
            "edit_contact_id": contact.pk,
            # optional: biar title & tombol ikut vendor meski render manual
            "entity_label": "Vendor",
            "entity_urls": "vendor",
        })
