from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy

from partners.models import Partner
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponseRedirect

from ..models import FreightQuotation, FreightQuotationStatus
from ..forms import FreightQuotationForm
from geo.models import Location
from core.utils import get_valid_days_default
from django.utils import timezone
from django.shortcuts import redirect
from core.models import Currency,SalesService,PaymentTerm
from django.shortcuts import redirect, get_object_or_404
from django.views import View

import sys


ALLOWED_DELETE_STATUSES = ("DRAFT", "CANCELLED", "EXPIRED")


class FqListView(LoginRequiredMixin, ListView):
    model = FreightQuotation
    template_name = "sales/quotation_list.html"
    context_object_name = "quotations"
    paginate_by = 20
    ordering = "-created_at" 

    def get_queryset(self):
        qs = (
            FreightQuotation.objects
            .select_related("customer", "sales_service", "origin", "destination")
            .order_by("-created_at")
        )

        request = self.request

        q            = (request.GET.get("q") or "").strip()
        statuses     = request.GET.getlist("status")
        currencies   = request.GET.getlist("currency")
        services     = request.GET.getlist("service")
        agents       = request.GET.getlist("agent")
        paymentterms = request.GET.getlist("payment_term")

        # Search
        if q:
            qs = qs.filter(
                Q(number__icontains=q) |
                Q(customer__name__icontains=q) |
                Q(customer__company_name__icontains=q) |
                Q(origin__name__icontains=q) |
                Q(destination__name__icontains=q)
            )

        if statuses:
            qs = qs.filter(status__in=statuses)

        if currencies:
            qs = qs.filter(currency_id__in=currencies)

        if services:
            qs = qs.filter(sales_service_id__in=services)

        if agents:
            qs = qs.filter(sales_user_id__in=agents)

        if paymentterms:
            qs = qs.filter(payment_term_id__in=paymentterms)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        # buat filter value yang dipilih user
        ctx.update(
            {
                # search / sorting param
                "q": request.GET.get("q", ""),
                "sort": request.GET.get("sort", ""),
                "dir": request.GET.get("dir", ""),
                "sp": request.GET.get("sp", ""),

                # ===== LIST PILIHAN FILTER =====
                "status_choices": FreightQuotationStatus.choices,
                "currencies": Currency.objects.order_by("code"),
                "services": SalesService.objects.filter(is_active=True).order_by("name"),
                "paymentterms": PaymentTerm.objects.order_by("name"),

                # sales agent: ambil partner individu
                "agents": Partner.objects.filter(is_individual=True).order_by("name"),

                # ===== NILAI FILTER YANG SEDANG DIPILIH =====
                "flt_statuses": request.GET.getlist("status"),
                "flt_currencies": request.GET.getlist("currency"),
                "flt_services": request.GET.getlist("service"),
                "flt_agents": request.GET.getlist("agent"),
                "flt_paymentterms": request.GET.getlist("payment_term"),
            }
        )

        return ctx



class FqSaveMixin:
    """
    Helper untuk ambil data shipper & consignee dari request.POST
    dan simpan ke field snapshot di FreightQuotation.
    """

    def _fill_shipper_consignee_from_request(self, obj: FreightQuotation):
        r = self.request.POST

        # ============ SHIPPER ============
        obj.shipper_contact_name = (r.get("shipper_contact_name") or "").strip()
        obj.shipper_phone = (r.get("shipper_phone") or "").strip()
        obj.shipper_address = (r.get("shipper_address") or "").strip()

        # FK shipper partner (hidden input name="shipper")
        shipper_id = (r.get("shipper") or "").strip()
        if shipper_id.isdigit():
            obj.shipper_id = int(shipper_id)
        else:
            obj.shipper = None

        # geo shipper: shipper_province, shipper_regency, shipper_district, shipper_village
        for part in ["province", "regency", "district", "village"]:
            key = f"shipper_{part}"
            val = (r.get(key) or "").strip()
            field_name = f"shipper_{part}_id"
            if val.isdigit():
                setattr(obj, field_name, int(val))
            else:
                setattr(obj, field_name, None)

        # ============ CONSIGNEE ============
        obj.consignee_name = (r.get("consignee_name") or "").strip()
        obj.consignee_phone = (r.get("consignee_phone") or "").strip()
        obj.consignee_address = (r.get("consignee_address") or "").strip()

        # geo consignee: consignee_province, consignee_regency, consignee_district, consignee_village
        for part in ["province", "regency", "district", "village"]:
            key = f"consignee_{part}"
            val = (r.get(key) or "").strip()
            field_name = f"consignee_{part}_id"
            if val.isdigit():
                setattr(obj, field_name, int(val))
            else:
                setattr(obj, field_name, None)

        # FK consignee partner
        consignee_id = (r.get("consignee") or "").strip()
        save_new = r.get("consignee_save_partner")  # checkbox "on" kalau dicentang

        if consignee_id.isdigit():
            # user pilih dari autocomplete partner
            obj.consignee_id = int(consignee_id)
        elif save_new and obj.consignee_name:
            # user tulis nama + centang "simpan sebagai contact baru"
            partner = Partner.objects.create(
                name=obj.consignee_name,
                company_name=obj.consignee_name,
                phone=obj.consignee_phone or "",
                address_line1=obj.consignee_address or "",
                province_id=obj.consignee_province_id,
                regency_id=obj.consignee_regency_id,
                district_id=obj.consignee_district_id,
                village_id=obj.consignee_village_id,
                is_individual=False,
            )
            obj.consignee = partner
        else:
            # tidak pilih partner & tidak minta simpan → FK boleh kosong
            if not obj.consignee_name:
                obj.consignee = None


from django.http import HttpResponse
from django.urls import reverse

class FqCreateView(LoginRequiredMixin, FqSaveMixin, CreateView):
    
    model = FreightQuotation
    form_class = FreightQuotationForm
    template_name = "sales/quotation_form.html"

    
    def form_valid(self, form):

        obj: FreightQuotation = form.save(commit=False)
        today = timezone.now().date()

        # quotation_date: kalau masih kosong → today
        if not obj.quotation_date:
            obj.quotation_date = today

        # status: default DRAFT
        if not obj.status:
            obj.status = FreightQuotationStatus.DRAFT

        # number: pakai next_number kalau belum di-set
        if not obj.number and hasattr(FreightQuotation, "next_number"):
            obj.number = FreightQuotation.next_number()

        # valid_until: +7 hari dari quotation_date kalau kosong
        if not obj.valid_until:
            base_date = obj.quotation_date or today
            obj.valid_until = base_date + timezone.timedelta(days=7)

        # sales_user otomatis dari user login
        if not obj.sales_user_id:
            obj.sales_user = self.request.user

        obj.save()
        self.object = obj

        # sementara: biar kelihatan sukses
        #return HttpResponse(f"OK — SAVED SUCCESSFULLY — ID: {obj.pk}")
        # atau pakai redirect:
        return redirect("sales:fq_detail", pk=obj.pk)
        # atau:
        # return super().form_valid(form)

    def form_invalid(self, form):
        # Debug tetap boleh ke console, tapi RESPON tetap ke template form
        print("=== FREIGHT FORM INVALID ===", file=sys.stderr)
        print(form.errors.as_json(), file=sys.stderr)
        print("================================", file=sys.stderr)

        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["provinces"] = Location.objects.filter(kind="province").order_by("name")
        return ctx
 
from django.views.generic import UpdateView  # pastikan ini di-import
class FqUpdateView(LoginRequiredMixin, FqSaveMixin, UpdateView):
    model = FreightQuotation
    form_class = FreightQuotationForm
    template_name = "sales/quotation_form.html"
    context_object_name = "quotation"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)

        # isi snapshot shipper & consignee dari POST kalau perlu
        self._fill_shipper_consignee_from_request(obj)

        obj.save()
        messages.success(self.request, f"Freight quotation {obj.number} berhasil diperbarui.")
        return redirect("sales:fq_detail", pk=obj.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fq = self.object

        ctx["provinces"] = Location.objects.filter(kind="province").order_by("name")

        def children(kind, parent_obj):
            if not parent_obj:
                return Location.objects.none()
            return Location.objects.filter(kind=kind, parent=parent_obj).order_by("name")

        # SHIPPER chain
        ctx["shipper_regencies"] = children("regency", fq.shipper_province)
        ctx["shipper_districts"] = children("district", fq.shipper_regency)
        ctx["shipper_villages"] = children("village", fq.shipper_district)

        # CONSIGNEE chain
        ctx["consignee_regencies"] = children("regency", fq.consignee_province)
        ctx["consignee_districts"] = children("district", fq.consignee_regency)
        ctx["consignee_villages"] = children("village", fq.consignee_district)

        ctx["page_title"] = f"Edit Freight Quotation {fq.number}"
        return ctx



class FqDetailView(LoginRequiredMixin, DetailView):
    model = FreightQuotation
    template_name = "sales/quotation_detail.html"
    context_object_name = "fq"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Freight Quotation {self.object.number}"
        return ctx



class FqDeleteView(LoginRequiredMixin, View):

   def post(self, request, pk, *args, **kwargs):
        fq = get_object_or_404(FreightQuotation, pk=pk)

        # Hanya boleh delete DRAFT / CANCELLED / EXPIRED
        if fq.status not in ALLOWED_DELETE_STATUSES:
            messages.error(
                request,
                "Quotation hanya bisa dihapus jika status Draft, Cancelled, atau Expired.",
            )
            return redirect("sales:freight_quotation_detail", pk=pk)

        number = fq.number
        fq.delete()
        messages.success(request, f"Quotation {number} berhasil dihapus.")
        return redirect("sales:freight_quotation_list")
   

class FqBulkDeleteView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        ids_raw = (request.POST.get("ids") or "").split(",")
        ids = [i for i in ids_raw if i.strip().isdigit()]

        if not ids:
            messages.error(request, "Tidak ada data yang dipilih.")
            return redirect("sales:freight_quotation_list")

        qs = FreightQuotation.objects.filter(pk__in=ids)

        # Boleh delete hanya yang status dalam ALLOWED_DELETE_STATUSES
        deletable = qs.filter(status__in=ALLOWED_DELETE_STATUSES)
        blocked = qs.exclude(status__in=ALLOWED_DELETE_STATUSES)

        deleted_count = deletable.count()
        blocked_count = blocked.count()

        if deleted_count:
            deletable.delete()
            messages.success(
                request,
                f"{deleted_count} quotation (Draft/Cancelled/Expired) berhasil dihapus.",
            )

        if blocked_count:
            messages.warning(
                request,
                f"{blocked_count} quotation tidak bisa dihapus (status bukan Draft/Cancelled/Expired).",
            )

        if not deleted_count and not blocked_count:
            messages.info(request, "Tidak ada quotation yang dihapus.")

        return redirect("sales:freight_quotation_list")
