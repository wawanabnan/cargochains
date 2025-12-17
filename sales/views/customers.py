# sales/views/customers.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy,reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.db.models import Q

from partners.models import Partner, PartnerRole
from sales.forms.customers import CustomerForm

from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from sales.forms.customer_contacts import CustomerContactForm


class CustomerQuerysetMixin:
    def get_queryset(self):
        customer_ids = PartnerRole.objects.filter(
            role_type__code__iexact="customer"
        ).values_list("partner_id", flat=True)

        return Partner.objects.filter(id__in=customer_ids).distinct()


class CustomerListView(LoginRequiredMixin, CustomerQuerysetMixin, ListView):
    model = Partner
    template_name = "customers/list.html"
    context_object_name = "customers"
    paginate_by = 20

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


from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from partners.models import PartnerRole, PartnerRoleTypes

class CustomerCreateView(CreateView):
    model = Partner
    form_class = CustomerForm
    template_name = "customers/form.html"

    def form_valid(self, form):
        obj = form.save(commit=False)

        # selalu customer entity utama tidak punya induk
        obj.company = None

        if obj.is_individual:
            # ✅ personal customer otomatis siap dokumen
            obj.is_sales_contact = True
            obj.is_billing_contact = True

            # kalau company_name kosong, biarkan; tapi name wajib
            obj.company_name = obj.company_name or ""
        else:
            # ✅ company customer
            # name disamakan company_name supaya legacy aman
            if obj.company_name and not obj.name:
                obj.name = obj.company_name

            # company bukan contact
            obj.is_sales_contact = False
            obj.is_billing_contact = False

        obj.save()

        # pastikan role customer
        role_customer = PartnerRoleTypes.objects.get(code__iexact="customer")
        PartnerRole.objects.get_or_create(partner=obj, role_type=role_customer)

        messages.success(self.request, "Customer berhasil dibuat.")
        return redirect(reverse("sales:customer_detail", args=[obj.pk]))


class CustomerUpdateView(LoginRequiredMixin, CustomerQuerysetMixin, UpdateView):
    model = Partner
    form_class = CustomerForm
    template_name = "customers/form.html"
    success_url = reverse_lazy("sales:customer_list")


class CustomerDetailView(LoginRequiredMixin, CustomerQuerysetMixin, DetailView):
    model = Partner
    template_name = "customers/detail.html"
    context_object_name = "customer"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = self.object

        # list contact tambahan (relasi company -> contacts)
        ctx["contacts"] = customer.contacts.all().order_by("id")

        # INI KUNCINYA: supaya modal tidak kosong
        ctx["contact_form"] = ctx.get("contact_form") or CustomerContactForm()

        # support auto-open modal dari querystring ?open_contact=1
        open_flag = (self.request.GET.get("open_contact") or "").strip()
        ctx["open_contact"] = bool(open_flag) and open_flag not in ("0", "false", "False", "no", "NO")

        return ctx



class CustomerDeleteView(LoginRequiredMixin, CustomerQuerysetMixin, DeleteView):
    model = Partner
    template_name = "customers/confirm_delete.html"
    success_url = reverse_lazy("sales:customer_list")


class CustomerContactCreateView(View):
    def post(self, request, pk):
        customer = get_object_or_404(Partner, pk=pk)

        form = CustomerContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.is_individual = True
            contact.company = customer   # ⬅️ link ke perusahaan induk
            contact.save()

            # OPTIONAL: kalau om mau otomatis beri role customer juga ke contact
            # (biasanya tidak perlu, tapi kalau logic list customer pakai role,
            # lebih aman jangan)
            # PartnerRole.objects.get_or_create(partner=contact, role_type=...)

            messages.success(request, "Contact berhasil ditambahkan.")
            return redirect(reverse("sales:customer_detail", args=[customer.pk]))

        # kalau invalid, balik ke detail dan buka modal lagi
        messages.error(request, f"Gagal menambah contact: {form.errors.as_text()}")
        return redirect(reverse("sales:customer_detail", args=[customer.pk]) + "?open_contact=1")


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

class CustomerContactUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        contact = get_object_or_404(Partner, pk=pk, is_individual=True)
        customer = contact.company  # induknya

        form = CustomerContactForm(request.POST, instance=contact)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.is_individual = True
            obj.company = customer
            obj.save()
            messages.success(request, "Contact berhasil diupdate.")
            return redirect(reverse("sales:customer_detail", args=[customer.pk]))

        # invalid -> balik ke detail, modal kebuka lagi, isi tetap ada
        contacts = customer.contacts.all().order_by("id")
        return render(request, "customers/detail.html", {
            "customer": customer,
            "contacts": contacts,
            "contact_form": form,
            "open_contact": True,
            "edit_contact_id": contact.pk,
        })
