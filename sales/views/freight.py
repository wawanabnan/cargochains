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
from core.models import Currency,SalesService,PaymentTerm
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.db import transaction

import sys


from django.contrib import messages
from django.urls import reverse




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


class FreightQuotationMixin:
    def _inject_geo_context(self, ctx):
        fq = None
        form = ctx.get("form")
        if form is not None and getattr(form, "instance", None):
            fq = form.instance

        ctx["provinces"] = Location.objects.filter(
            kind="province"
        ).order_by("name")

        def children(parent_id):
            if not parent_id:
                return Location.objects.none()
            return Location.objects.filter(parent_id=parent_id).order_by("name")

        if fq and fq.pk:
            ctx["shipper_regencies"]  = children(getattr(fq, "shipper_province_id", None))
            ctx["shipper_districts"]  = children(getattr(fq, "shipper_regency_id", None))
            ctx["shipper_villages"]   = children(getattr(fq, "shipper_district_id", None))

            ctx["consignee_regencies"] = children(getattr(fq, "consignee_province_id", None))
            ctx["consignee_districts"] = children(getattr(fq, "consignee_regency_id", None))
            ctx["consignee_villages"]  = children(getattr(fq, "consignee_district_id", None))
        else:
            # ADD mode → biarin kosong, nanti diisi JS via /geo/children/
            ctx["shipper_regencies"]   = Location.objects.none()
            ctx["shipper_districts"]   = Location.objects.none()
            ctx["shipper_villages"]    = Location.objects.none()
            ctx["consignee_regencies"] = Location.objects.none()
            ctx["consignee_districts"] = Location.objects.none()
            ctx["consignee_villages"]  = Location.objects.none()

        return ctx

from django.http import HttpResponse
from django.urls import reverse
class FqCreateView(LoginRequiredMixin, FreightQuotationMixin, CreateView):
    model = FreightQuotation
    form_class = FreightQuotationForm
    template_name = "sales/quotation_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_mode"] = "add"
        return self._inject_geo_context(ctx)
    
    def get_success_url(self):
        return reverse("sales:fq_detail", args=[self.object.pk])


from django.views.generic import UpdateView

class FqUpdateView(LoginRequiredMixin, FreightQuotationMixin, UpdateView):
    model = FreightQuotation
    form_class = FreightQuotationForm
    template_name = "sales/quotation_form.html"
    context_object_name = "fq"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_mode"] = "edit"
        return self._inject_geo_context(ctx)

    def get_success_url(self):
        return reverse("sales:fq_detail", args=[self.object.pk])


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



from core.utils import get_next_number
class FqStatusUpdateView(LoginRequiredMixin, View):
    """
    Ubah status FreightQuotation via POST.

    Aksi yang didukung:
    - sent           -> ubah status ke SENT
    - accepted       -> ubah status ke ACCEPTED
    - cancelled      -> ubah status ke CANCELLED
    - expired        -> ubah status ke EXPIRED
    - generate_order -> buat FreightOrder (Draft) + set quotation = ORDERED
    """

    def post(self, request, pk, *args, **kwargs):
        fq = get_object_or_404(FreightQuotation, pk=pk)

        action = (request.POST.get("action") or "").strip().lower()
        current = fq.status or FreightQuotationStatus.DRAFT

        # Status final: tidak boleh diubah lagi (kecuali generate_order tidak relevan juga)
        terminal_statuses = {
            FreightQuotationStatus.CANCELLED,
            FreightQuotationStatus.EXPIRED,
            FreightQuotationStatus.ORDERED,
        }
        if current in terminal_statuses and action != "generate_order":
            messages.warning(
                request,
                f"Quotation dengan status {fq.get_status_display()} tidak dapat diubah lagi."
            )
            return redirect("sales:fq_detail", pk=fq.pk)

        # ---- aksi status biasa ----
        if action in ("sent", "accepted", "cancelled", "expired"):
            return self._handle_simple_status(request, fq, action)

        # ---- aksi generate_order ----
        if action == "generate_order":
            return self._handle_generate_order(request, fq)

        # kalau sampai sini, action memang tidak dikenali
        messages.error(request, "Aksi status tidak dikenal.")
        return redirect("sales:fq_detail", pk=fq.pk)

    # ----------------------------------------------------------
    # Status sederhana: sent / accepted / cancelled / expired
    # ----------------------------------------------------------
    def _handle_simple_status(self, request, fq, action: str):
        mapping = {
            "sent":      FreightQuotationStatus.SENT,
            "accepted":  FreightQuotationStatus.ACCEPTED,
            "cancelled": FreightQuotationStatus.CANCELLED,
            "expired":   FreightQuotationStatus.EXPIRED,
        }
        msg_map = {
            "sent":      "Quotation ditandai sebagai SENT.",
            "accepted":  "Quotation ditandai sebagai ACCEPTED.",
            "cancelled": "Quotation dibatalkan.",
            "expired":   "Quotation ditandai EXPIRED.",
        }

        new_status = mapping[action]
        current = fq.status or FreightQuotationStatus.DRAFT

        # aturan transisi sederhana
        allowed_transitions = {
            FreightQuotationStatus.DRAFT: {
                FreightQuotationStatus.SENT,
                FreightQuotationStatus.CANCELLED,
            },
            FreightQuotationStatus.SENT: {
                FreightQuotationStatus.ACCEPTED,
                FreightQuotationStatus.CANCELLED,
                FreightQuotationStatus.EXPIRED,
            },
            FreightQuotationStatus.ACCEPTED: {
                FreightQuotationStatus.CANCELLED,
            },
        }

        if new_status not in allowed_transitions.get(current, set()):
            messages.error(
                request,
                f"Tidak dapat mengubah status dari {fq.get_status_display()} ke {new_status}."
            )
            return redirect("sales:fq_detail", pk=fq.pk)

        fq.status = new_status
        update_fields = ["status"]
        if hasattr(fq, "updated_at"):
            update_fields.append("updated_at")
        fq.save(update_fields=update_fields)

        messages.success(request, msg_map[action])
        return redirect("sales:fq_detail", pk=fq.pk)

    # ----------------------------------------------------------
    # generate_order: buat FreightOrder + set fq.status = ORDERED
    # ----------------------------------------------------------
    def _handle_generate_order(self, request, fq):
        from sales.freight import FreightOrder  # model order

        current = fq.status or FreightQuotationStatus.DRAFT

        # Hanya boleh generate dari ACCEPTED
        if current != FreightQuotationStatus.ACCEPTED:
            messages.error(
                request,
                "Generate Order hanya bisa dilakukan dari status ACCEPTED."
            )
            return redirect("sales:fq_detail", pk=fq.pk)

        try:
            order = self.generate_order_from_fq(fq, request.user, FreightOrder)
        except Exception as exc:
            messages.error(request, f"Gagal generate order dari quotation ini: {exc}")
            return redirect("sales:fq_detail", pk=fq.pk)

        # Set status quotation -> ORDERED
        fq.status = FreightQuotationStatus.ORDERED
        update_fields = ["status"]
        if hasattr(fq, "updated_at"):
            update_fields.append("updated_at")
        fq.save(update_fields=update_fields)

        display_no = getattr(order, "number", order.pk)
        messages.success(
            request,
            f"Freight Order {display_no} (Draft) berhasil dibuat dari quotation {fq.number}."
        )

        return redirect("sales:fq_detail", pk=fq.pk)

    # ----------------------------------------------------------
    # core generator FreightOrder dari FreightQuotation
    # ----------------------------------------------------------
    @transaction.atomic
    def generate_order_from_fq(self, fq, user, FreightOrder):
        """
        Membuat FreightOrder baru dari FreightQuotation.
        Hanya mengirim field yang BENAR-BENAR ADA di FreightOrder.
        """
        # daftar field valid di FreightOrder
        allowed_fields = {
            f.name
            for f in FreightOrder._meta.get_fields()
            if getattr(f, "concrete", False) and not f.auto_created
        }

        # tentukan order_date (NOT NULL) :
        order_date_value = getattr(fq, "quotation_date", None) or timezone.now().date()

        # kandidat data copy dari quotation
        base_data = {
            # header
            "customer": fq.customer,
            "sales_service": getattr(fq, "sales_service", None),
            "sales_agency": getattr(fq, "sales_agency", None),
            "payment_term": fq.payment_term,
            "currency": getattr(fq, "currency", None),
            "sales_user": fq.sales_user or user,

            # tanggal order
            "order_date": order_date_value,

            # route
            "origin": fq.origin,
            "destination": fq.destination,
            "shipment_plan_date": fq.shipment_plan_date,

            # cargo
            "cargo_name": fq.cargo_name,
            "hs_code": getattr(fq, "hs_code", None),
            "commodity": getattr(fq, "commodity", None),
            "package_count": fq.package_count,
            "package_type": getattr(fq, "package_type", None),
            "gross_weight": fq.gross_weight,
            "volume_cbm": fq.volume_cbm,
            "weight_uom": getattr(fq, "weight_uom", None),
            "volume_uom": getattr(fq, "volume_uom", None),

            # shipper
            "shipper": getattr(fq, "shipper", None),
            "shipper_contact_name": getattr(fq, "shipper_contact_name", None),
            "shipper_phone": getattr(fq, "shipper_phone", None),
            "shipper_province": getattr(fq, "shipper_province", None),
            "shipper_regency": getattr(fq, "shipper_regency", None),
            "shipper_district": getattr(fq, "shipper_district", None),
            "shipper_village": getattr(fq, "shipper_village", None),
            "shipper_address": getattr(fq, "shipper_address", None),

            # consignee
            "consignee": getattr(fq, "consignee", None),
            "consignee_name": getattr(fq, "consignee_name", None),
            "consignee_phone": getattr(fq, "consignee_phone", None),
            "consignee_province": getattr(fq, "consignee_province", None),
            "consignee_regency": getattr(fq, "consignee_regency", None),
            "consignee_district": getattr(fq, "consignee_district", None),
            "consignee_village": getattr(fq, "consignee_village", None),
            "consignee_address": getattr(fq, "consignee_address", None),

            # pricing
            "quantity": fq.quantity,
            "unit_price": fq.unit_price,
            "amount": fq.amount,
            "discount_percent": getattr(fq, "discount_percent", None),
            "discount_amount": getattr(fq, "discount_amount", None),
            "tax_percent": fq.tax_percent,
            "tax_amount": fq.tax_amount,
            "total_amount": fq.total_amount,

            # notes
            "notes_customer": getattr(fq, "notes_customer", None),
            "notes_internal": getattr(fq, "notes_internal", None),
        }

        # filter: hanya field yang:
        # 1) ada di FreightOrder
        # 2) value tidak None
        data = {
            name: value
            for name, value in base_data.items()
            if name in allowed_fields and value is not None
        }

        # ====== NOMOR ORDER (PENTING, BIAR GA DUPLICATE '') ======
        # pakai cara yang sama seperti FreightQuotation,
        # bedanya kodenya FREIGHT_ORDER
        if "number" in allowed_fields and not data.get("number"):
            # sesuaikan argumen pertama dengan yang dipakai FQ:
            # kalau di FreightQuotation pakai get_next_number("sales", "FREIGHT_QUOTATION")
            # maka di sini:
            data["number"] = get_next_number("sales", "FREIGHT_ORDER")

        # link ke quotation kalau FO punya FK yang cocok
        for fk_name in ("freight_quotation", "quotation", "source_quotation"):
            if fk_name in allowed_fields:
                data[fk_name] = fq
                break

        # jangan override status, biarkan default FO (misal DRAFT)
        if "status" in data:
            data.pop("status")

        order = FreightOrder.objects.create(**data)
        return order


from sales.freight import (
    FreightQuotation,
    FreightQuotationStatus,
    FreightOrder,
    FreightOrderStatus,
)


class FoListView(LoginRequiredMixin, ListView):
    model = FreightOrder
    template_name = "sales/order_list.html"
    context_object_name = "orders"
    paginate_by = 20
    ordering = "-created_at"

    def get_queryset(self):
        qs = (
            FreightOrder.objects
            .select_related("customer", "origin", "destination", "sales_service", "payment_term")
            .order_by("-created_at")
        )

        request = self.request

        q            = (request.GET.get("q") or "").strip()
        statuses     = request.GET.getlist("status")
        services     = request.GET.getlist("service")
        paymentterms = request.GET.getlist("payment_term")

        # Search sederhana
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

        if services:
            qs = qs.filter(sales_service_id__in=services)

        if paymentterms:
            qs = qs.filter(payment_term_id__in=paymentterms)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        ctx.update(
            {
                # search / sorting param (disiapkan untuk nanti kalau mau sorting)
                "q": request.GET.get("q", ""),
                "sort": request.GET.get("sort", ""),
                "dir": request.GET.get("dir", ""),
                "sp": request.GET.get("sp", ""),

                # pilihan filter
                "status_choices": FreightOrderStatus.choices,
                "services": SalesService.objects.filter(is_active=True).order_by("name"),
                "paymentterms": PaymentTerm.objects.order_by("name"),

                # nilai filter aktif
                "flt_statuses": request.GET.getlist("status"),
                "flt_services": request.GET.getlist("service"),
                "flt_paymentterms": request.GET.getlist("payment_term"),
            }
        )
        return ctx


class FoDetailView(LoginRequiredMixin, DetailView):
    model = FreightOrder
    template_name = "sales/order_detail.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Freight Order {self.object.number}"
        return ctx



class FoStatusUpdateView(LoginRequiredMixin, View):
    """
    Ubah status FreightOrder via POST.
    Aksi diambil dari field POST 'action':
    - sent
    - on_progress
    - completed
    - cancelled
    - holded
    """

    def post(self, request, pk):
        order = get_object_or_404(FreightOrder, pk=pk)

        # Permission sederhana: hanya sales terkait / atau yang punya izin global
        if not request.user.has_perm("sales.view_all_sales"):
            if order.sales_user_id and order.sales_user_id != request.user.id:
                messages.error(request, "Anda tidak berhak mengubah status order ini.")
                return redirect(self._redirect_url(order))

        action = (request.POST.get("action") or "").lower()
        current = order.status or FreightOrderStatus.DRAFT

        terminal_statuses = {
            FreightOrderStatus.COMPLETED,
            FreightOrderStatus.CANCELLED,
        }

        # 1) Kalau sudah final → tidak boleh diubah lagi
        if current in terminal_statuses:
            messages.error(
                request,
                f"Order dengan status {order.get_status_display()} tidak dapat diubah lagi."
            )
            return redirect(self._redirect_url(order))

        # 2) Mapping action -> status baru
        mapping = {
            "sent":        FreightOrderStatus.SENT,
            "on_progress": FreightOrderStatus.ON_PROGRESS,
            "completed":   FreightOrderStatus.COMPLETED,
            "cancelled":   FreightOrderStatus.CANCELLED,
            "holded":      FreightOrderStatus.HOLDED,
        }

        if action not in mapping:
            messages.error(request, "Aksi status tidak dikenal.")
            return redirect(self._redirect_url(order))

        new_status = mapping[action]

        # 3) Aturan transisi
        allowed_transitions = {
            FreightOrderStatus.DRAFT: {
                FreightOrderStatus.SENT,
                FreightOrderStatus.CANCELLED,
                FreightOrderStatus.HOLDED,
            },
            FreightOrderStatus.SENT: {
                FreightOrderStatus.ON_PROGRESS,
                FreightOrderStatus.CANCELLED,
                FreightOrderStatus.HOLDED,
            },
            FreightOrderStatus.ON_PROGRESS: {
                FreightOrderStatus.COMPLETED,
                FreightOrderStatus.CANCELLED,
                FreightOrderStatus.HOLDED,
            },
            FreightOrderStatus.HOLDED: {
                FreightOrderStatus.SENT,
                FreightOrderStatus.CANCELLED,
            },
        }

        if new_status not in allowed_transitions.get(current, set()):
            messages.error(
                request,
                f"Tidak dapat mengubah status dari {order.get_status_display()} "
                f"ke {new_status.label}."
            )
            return redirect(self._redirect_url(order))

        order.status = new_status
        order.save(update_fields=["status"])

        messages.success(
            request,
            f"Status order berhasil diubah menjadi {order.get_status_display()}."
        )
        return redirect(self._redirect_url(order))

    def _redirect_url(self, order):
        return reverse("sales:fo_detail", args=[order.pk])
