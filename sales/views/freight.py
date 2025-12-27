from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
)

from decimal import Decimal, InvalidOperation
import datetime

from partners.models import Partner, PartnerRole
from geo.models import Location
from core.models.currencies import Currency
from core.models.services import SalesService
from core.models.payment_terms import PaymentTerm



from core.utils import get_next_number, get_valid_days_default

from sales.forms.freights import (
    FreightQuotationForm,
    GenerateOrderForm,
    FreightOrderEditForm,
)

from sales.freight import FreightOrder, FreightOrderStatus
from django.db.models import Q
from sales.freight import FreightQuotation, FreightQuotationStatus




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
              qs = qs.filter(sales_agency_id__in=agents)

        if paymentterms:
            qs = qs.filter(payment_term_id__in=paymentterms)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        try:
            agency_ids = PartnerRole.objects.filter(
                role_type__code__iexact="agency"
            ).values_list("partner_id", flat=True)

            agents_qs = Partner.objects.filter(id__in=agency_ids).order_by("name")
        except Exception:
            agents_qs = Partner.objects.none()



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
                "agents": agents_qs ,

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
        form = ctx.get("form")
        fq = None
        if form is not None and getattr(form, "instance", None):
            fq = form.instance

        # PROVINCE SELALU ADA
        ctx["provinces"] = Location.objects.filter(
            kind="province"
        ).order_by("name")

        def children(parent_id):
            if not parent_id:
                return Location.objects.none()
            return Location.objects.filter(parent_id=parent_id).order_by("name")

        # DEFAULT: kosong dulu
        ctx["shipper_regencies"]   = Location.objects.none()
        ctx["shipper_districts"]   = Location.objects.none()
        ctx["shipper_villages"]    = Location.objects.none()
        ctx["consignee_regencies"] = Location.objects.none()
        ctx["consignee_districts"] = Location.objects.none()
        ctx["consignee_villages"]  = Location.objects.none()

        # 1) KASUS FORM BOUND (POST) → pakai data yang dikirim user
        if form is not None and form.is_bound:
            sp_prov_id = form.data.get("shipper_province") or None
            sp_reg_id  = form.data.get("shipper_regency") or None
            sp_dist_id = form.data.get("shipper_district") or None

            cg_prov_id = form.data.get("consignee_province") or None
            cg_reg_id  = form.data.get("consignee_regency") or None
            cg_dist_id = form.data.get("consignee_district") or None

            if sp_prov_id:
                ctx["shipper_regencies"] = children(sp_prov_id)
            if sp_reg_id:
                ctx["shipper_districts"] = children(sp_reg_id)
            if sp_dist_id:
                ctx["shipper_villages"] = children(sp_dist_id)

            if cg_prov_id:
                ctx["consignee_regencies"] = children(cg_prov_id)
            if cg_reg_id:
                ctx["consignee_districts"] = children(cg_reg_id)
            if cg_dist_id:
                ctx["consignee_villages"] = children(cg_dist_id)

            return ctx

        # 2) KASUS EDIT (GET) → pakai instance yang sudah tersimpan
        if fq and fq.pk:
            ctx["shipper_regencies"]   = children(getattr(fq, "shipper_province_id", None))
            ctx["shipper_districts"]   = children(getattr(fq, "shipper_regency_id", None))
            ctx["shipper_villages"]    = children(getattr(fq, "shipper_district_id", None))

            ctx["consignee_regencies"] = children(getattr(fq, "consignee_province_id", None))
            ctx["consignee_districts"] = children(getattr(fq, "consignee_regency_id", None))
            ctx["consignee_villages"]  = children(getattr(fq, "consignee_district_id", None))

        # 3) KASUS ADD (GET pertama) → tetap kosong, nanti diisi JS
        return ctx


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
        ctx["generate_order_form"] = GenerateOrderForm(
            initial={
                "ref_date": self.object.quotation_date,
                "down_payment": getattr(self.object, "down_payment", ""),
            }
        )
        ctx.setdefault("open_generate_order_modal", False)
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



#---------------------------------------------status update-------------------------------------------#
    """
    Ubah status FreightQuotation via POST.

    Aksi:
    - sent           -> SENT
    - accepted       -> ACCEPTED
    - cancelled      -> CANCELLED
    - expired        -> EXPIRED
    - generate_order -> buat FreightOrder (Draft) + set FQ = ORDERED
    """

    def post(self, request, pk, *args, **kwargs):
        fq = get_object_or_404(FreightQuotation, pk=pk)

        action = (request.POST.get("action") or "").strip().lower()
        current = fq.status or FreightQuotationStatus.DRAFT

        # status final: tidak boleh diutak-atik lagi (kecuali generate_order)
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

        if action in ("sent", "accepted", "cancelled", "expired"):
            return self._handle_simple_status(request, fq, action)

        if action == "generate_order":
            return self._handle_generate_order(request, fq)

        messages.error(request, "Aksi status tidak dikenal.")
        return redirect("sales:fq_detail", pk=fq.pk)

    # ----------------------------------------------------------
    # 1) Status sederhana
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
    # 2) generate_order (support AJAX + non-AJAX)
    # ----------------------------------------------------------

    def _handle_generate_order(self, request, fq, is_ajax):
        current = fq.status or FreightQuotationStatus.DRAFT

        # hanya boleh generate dari ACCEPTED
        if current != FreightQuotationStatus.ACCEPTED:
            msg = "Generate Order hanya bisa dilakukan dari status ACCEPTED."
            if is_ajax:
                return JsonResponse(
                    {"success": False, "non_field_errors": [msg]},
                    status=400,
                )
            messages.error(request, msg)
            return redirect(request.META.get("HTTP_REFERER", "/"))

        form = GenerateOrderForm(request.POST)

        # FORM INVALID → balas JSON utk modal
        if not form.is_valid():
            if is_ajax:
                errors = {
                    field: [str(e) for e in errs]
                    for field, errs in form.errors.items()
                }
                return JsonResponse(
                    {"success": False, "errors": errors},
                    status=400,
                )

            # non-AJAX fallback (kalau suatu saat dibuka tanpa modal)
            context = {
                "fq": fq,
                "generate_order_form": form,
                "open_generate_order_modal": True,
            }
            return render(
                request,
                "sales/freight_quotation_detail.html",  # sesuaikan jika beda
                context,
            )

        # FORM VALID → buat order
        cd = form.cleaned_data
        ref_type = cd["ref_type"]
        ref_number = cd["ref_number"]
        ref_date = cd["ref_date"]
        down_payment = cd["down_payment"]

        try:
            order = self._create_order(
                fq=fq,
                ref_type=ref_type,
                ref_number=ref_number,
                ref_date=ref_date,
                down_payment=down_payment,
                user=request.user,
            )
        except Exception as exc:
            msg = f"Gagal generate order dari quotation ini: {exc}"
            if is_ajax:
                return JsonResponse(
                    {"success": False, "non_field_errors": [msg]},
                    status=500,
                )
            messages.error(request, msg)
            return redirect(request.META.get("HTTP_REFERER", "/"))

        # update status FQ → ORDERED (+ simpan DP kalau ada field-nya)
        fq.status = FreightQuotationStatus.ORDERED
        update_fields = ["status"]

        if hasattr(fq, "down_payment") and down_payment is not None:
            fq.down_payment = down_payment
            update_fields.append("down_payment")

        if hasattr(fq, "updated_at"):
            update_fields.append("updated_at")

        fq.save(update_fields=update_fields)

        display_no = getattr(order, "number", order.pk)
        success_msg = (
            f"Freight Order {display_no} (Draft) berhasil dibuat "
            f"dari quotation {fq.number}."
        )

        # >>> URL DETAIL FREIGHT ORDER (GANTI NAMA URL JIKA PERLU)
        fo_detail_url = reverse("sales:fo_detail", args=[order.pk])

        if is_ajax:
            # JS di modal akan pakai redirect_url ini
            fo_detail_url = reverse("sales:fo_detail", args=[order.pk])
            return JsonResponse(
                {
                    "success": True,
                    "message": success_msg,
                    "order_id": order.pk,
                    "order_number": getattr(order, "number", ""),
                    "redirect_url": fo_detail_url,   # <<< penting
                }
            )

        messages.success(request, success_msg)
        return redirect(fo_detail_url)  # <<< non-AJAX langsung ke FO detail



        # ----------------------------------------------------------
        # 3) Generator FreightOrder dari FreightQuotation
        # ----------------------------------------------------------
        @transaction.atomic
        def generate_order_from_fq(
            self,
            fq,
            user,
            FreightOrder,
            ref_type=None,
            ref_number=None,
            ref_date=None,
            down_payment=None,
        ):
            allowed_fields = {
                f.name
                for f in FreightOrder._meta.get_fields()
                if getattr(f, "concrete", False) and not f.auto_created
            }

            order_date_value = (
                ref_date
                or getattr(fq, "quotation_date", None)
                or timezone.now().date()
            )

            base_data = {
                # header
                "customer": fq.customer,
                "sales_service": getattr(fq, "sales_service", None),
                "sales_agency": getattr(fq, "sales_agency", None),
                "payment_term": fq.payment_term,
                "sales_user": fq.sales_user or user,

                # tanggal order
                "order_date": order_date_value,

                # route
                "origin": fq.origin,
                "destination": fq.destination,
                "shipment_plan_date": fq.shipment_plan_date,

                # cargo
                "cargo_name": fq.cargo_name,
                "package_count": fq.package_count,
                "package_type": getattr(fq, "package_type", None),
                "gross_weight": fq.gross_weight,
                "volume_cbm": fq.volume_cbm,
                "weight_uom": getattr(fq, "weight_uom", None),
                "volume_uom": getattr(fq, "volume_uom", None),

                # shipper snapshot
                "shipper_name": getattr(fq, "shipper_contact_name", "") or "",
                "shipper_address": getattr(fq, "shipper_address", "") or "",

                # consignee snapshot
                "consignee_name": getattr(fq, "consignee_name", "") or "",
                "consignee_address": getattr(fq, "consignee_address", "") or "",

                # pricing
                "quantity": fq.quantity,
                "unit_price": fq.unit_price,
                "amount": fq.amount,
                "discount_percent": getattr(fq, "discount_percent", 0),
                "discount_amount": getattr(fq, "discount_amount", 0),
                "tax_percent": fq.tax_percent,
                "tax_amount": fq.tax_amount,
                "down_payment": down_payment if down_payment is not None else getattr(fq, "down_payment", 0),
                "total_amount": fq.total_amount,

                # reference
                "reference_type": ref_type or None,
                "reference_number": ref_number or None,
                "reference_date": ref_date or None,
            }

            data = {
                name: value
                for name, value in base_data.items()
                if name in allowed_fields and value is not None
            }

            if "number" in allowed_fields and not data.get("number"):
                data["number"] = get_next_number("sales", "FREIGHT_ORDER")

            for fk_name in ("freight_quotation", "quotation", "source_quotation"):
                if fk_name in allowed_fields:
                    data[fk_name] = fq
                    break

            if "status" in allowed_fields:
                data["status"] = FreightOrderStatus.DRAFT

            order = FreightOrder.objects.create(**data)
            return order
    
#-----------------------------------Status Update--------------------------------

class FqStatusUpdateView(LoginRequiredMixin, View):
    """
    Ubah status FreightQuotation + Generate Freight Order.

    Dipakai di path:
      freight-quotations/<int:pk>/status/   name="fq_change_status"

    Mendukung:
    - aksi status biasa: sent / accepted / cancelled / expired
    - generate_order: buat FreightOrder (Draft) dari FreightQuotation (ACCEPTED)
    - AJAX: balas JSON (dipakai di modal)
    - non-AJAX: redirect + messages (fallback)
    """

    def post(self, request, pk, *args, **kwargs):
        fq = get_object_or_404(FreightQuotation, pk=pk)
        action = (request.POST.get("action") or "").strip().lower()
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if action == "generate_order":
            return self._handle_generate_order(request, fq, is_ajax)

        # selain itu dianggap perubahan status biasa
        return self._handle_simple_status(request, fq, action, is_ajax)

    # ------------------------------------------------------------------
    # 1) STATUS BIASA: sent / accepted / cancelled / expired
    # ------------------------------------------------------------------
    def _handle_simple_status(self, request, fq, action, is_ajax):
        mapping = {
            "sent": FreightQuotationStatus.SENT,
            "accepted": FreightQuotationStatus.ACCEPTED,
            "cancelled": FreightQuotationStatus.CANCELLED,
            "expired": FreightQuotationStatus.EXPIRED,
        }
        msg_map = {
            "sent": "Quotation ditandai sebagai SENT.",
            "accepted": "Quotation ditandai sebagai ACCEPTED.",
            "cancelled": "Quotation dibatalkan.",
            "expired": "Quotation ditandai EXPIRED.",
        }

        if action not in mapping:
            msg = "Aksi status tidak dikenal."
            if is_ajax:
                return JsonResponse(
                    {"success": False, "non_field_errors": [msg]},
                    status=400,
                )
            messages.error(request, msg)
            return redirect(request.META.get("HTTP_REFERER", "/"))

        new_status = mapping[action]
        current = fq.status or FreightQuotationStatus.DRAFT

        # aturan transisi status
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
            msg = (
                f"Tidak dapat mengubah status dari "
                f"{fq.get_status_display()} ke {new_status}."
            )
            if is_ajax:
                return JsonResponse(
                    {"success": False, "non_field_errors": [msg]},
                    status=400,
                )
            messages.error(request, msg)
            return redirect(request.META.get("HTTP_REFERER", "/"))

        fq.status = new_status
        update_fields = ["status"]
        if hasattr(fq, "updated_at"):
            update_fields.append("updated_at")
        fq.save(update_fields=update_fields)

        msg = msg_map[action]
        if is_ajax:
            return JsonResponse(
                {
                    "success": True,
                    "message": msg,
                    "new_status": fq.status,
                }
            )

        messages.success(request, msg)
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # ------------------------------------------------------------------
    # 2) GENERATE ORDER (dipanggil dari modal AJAX)
    # ------------------------------------------------------------------
    def _handle_generate_order(self, request, fq, is_ajax):
        current = fq.status or FreightQuotationStatus.DRAFT

        # hanya boleh generate dari ACCEPTED
        if current != FreightQuotationStatus.ACCEPTED:
            msg = "Generate Order hanya bisa dilakukan dari status ACCEPTED."
            if is_ajax:
                return JsonResponse(
                    {"success": False, "non_field_errors": [msg]},
                    status=400,
                )
            messages.error(request, msg)
            return redirect(request.META.get("HTTP_REFERER", "/"))

        form = GenerateOrderForm(request.POST)

        # FORM INVALID → balas JSON utk modal
        if not form.is_valid():
            if is_ajax:
                errors = {
                    field: [str(e) for e in errs]
                    for field, errs in form.errors.items()
                }
                return JsonResponse(
                    {"success": False, "errors": errors},
                    status=400,
                )

            # non-AJAX fallback (kalau suatu saat dibuka tanpa modal)
            context = {
                "fq": fq,
                "generate_order_form": form,
                "open_generate_order_modal": True,
            }
            return render(
                request,
                "sales/freight_quotation_detail.html",  # sesuaikan jika beda
                context,
            )

        # FORM VALID → buat order
        cd = form.cleaned_data
        ref_type = cd["ref_type"]
        ref_number = cd["ref_number"]
        ref_date = cd["ref_date"]
        down_payment = cd["down_payment"]

        try:
            order = self._create_order(
                fq=fq,
                ref_type=ref_type,
                ref_number=ref_number,
                ref_date=ref_date,
                down_payment=down_payment,
                user=request.user,
            )
        except Exception as exc:
            msg = f"Gagal generate order dari quotation ini: {exc}"
            if is_ajax:
                return JsonResponse(
                    {"success": False, "non_field_errors": [msg]},
                    status=500,
                )
            messages.error(request, msg)
            return redirect(request.META.get("HTTP_REFERER", "/"))

        # update status FQ → ORDERED (+ simpan DP kalau ada field-nya)
        fq.status = FreightQuotationStatus.ORDERED
        update_fields = ["status"]

        if hasattr(fq, "down_payment") and down_payment is not None:
            fq.down_payment = down_payment
            update_fields.append("down_payment")

        if hasattr(fq, "updated_at"):
            update_fields.append("updated_at")

        fq.save(update_fields=update_fields)

        display_no = getattr(order, "number", order.pk)
        success_msg = (
            f"Freight Order {display_no} (Draft) berhasil dibuat "
            f"dari quotation {fq.number}."
        )

        if is_ajax:
            # JS di modal akan pakai window.location.href (halaman detail reload)
            return JsonResponse(
                {
                    "success": True,
                    "message": success_msg,
                    "order_id": order.pk,
                    "order_number": getattr(order, "number", ""),
                }
            )

        messages.success(request, success_msg)
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # ------------------------------------------------------------------
    # 3) CREATE ORDER dari QUOTATION
    # ------------------------------------------------------------------
    @transaction.atomic
    def _create_order(self, fq, ref_type, ref_number, ref_date, down_payment, user):
        """
        Buat FreightOrder Draft dari FreightQuotation.

        - Menyalin field yang namanya sama antara FreightQuotation & FreightOrder.
        - Men-set field khusus: quotation, reference_*, order_date, sales_user,
          number, status, down_payment.
        """
        # field konkret FreightOrder
        allowed = {
            f.name
            for f in FreightOrder._meta.get_fields()
            if getattr(f, "concrete", False) and not f.auto_created
        }

        data = {}

        # 1) salin semua field yang namanya sama di FQ & FO
        for name in allowed:
            if hasattr(fq, name):
                data[name] = getattr(fq, name)

        # 2) field khusus relasi ke quotation
        if "quotation" in allowed:
            data["quotation"] = fq

        # 3) reference (kalau field-nya ada)
        if "reference_type" in allowed:
            data["reference_type"] = ref_type
        if "reference_number" in allowed:
            data["reference_number"] = ref_number
        if "reference_date" in allowed:
            data["reference_date"] = ref_date

        # 4) order_date (fallback ke quotation_date atau hari ini)
        if "order_date" in allowed:
            order_date = (
                ref_date
                or getattr(fq, "quotation_date", None)
                or timezone.now().date()
            )
            data["order_date"] = order_date

        # 5) sales_user (kalau belum terisi)
        if "sales_user" in allowed and not data.get("sales_user"):
            data["sales_user"] = getattr(fq, "sales_user", None) or user

        # 6) down_payment override dari form, kalau field ada
        if "down_payment" in allowed and down_payment is not None:
            data["down_payment"] = down_payment

        # 6a) CURRENCY: copy dari quotation kalau field ada & belum ke-set
        if "currency" in allowed:
            if not data.get("currency"):
            # kalau FQ punya currency -> pakai itu
                currency = getattr(fq, "currency", None)
                if currency is not None:
                    data["currency"] = currency
                else:
                    # fallback IDR kalau mau (optional, but useful)
                    try:
                        from core.models import Currency
                        data["currency"] = Currency.objects.get(code="IDR")
                    except Exception:
                        # kalau master IDR belum ada, biarkan null
                        pass     

        # 7) auto-number kalau perlu
        if "number" in allowed and not data.get("number"):
            data["number"] = get_next_number("sales", "FREIGHT_ORDER")

        # 8) status = DRAFT
        if "status" in allowed:
            data["status"] = FreightOrderStatus.DRAFT

        # buang nilai None, baru create
        clean_data = {k: v for k, v in data.items() if v is not None}

        order = FreightOrder.objects.create(**clean_data)
        return order




#--------------------------------------Freight Order logic-----------------------
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
        order = self.object

        # Form untuk modal edit – hanya jika status Draft
        if order.status == FreightOrderStatus.DRAFT:
            ctx["edit_form"] = FreightOrderEditForm(instance=order)
        else:
            ctx["edit_form"] = None

        ctx["page_title"] = f"Freight Order {order.number}"
        return ctx


class FoStatusUpdateView(LoginRequiredMixin, View):
    """
    Ubah status FreightOrder via POST.
    Aksi diambil dari field POST 'action':
    - in_progress
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
            "in_progress": FreightOrderStatus.IN_PROGRESS,
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
                FreightOrderStatus.IN_PROGRESS,
                FreightOrderStatus.CANCELLED,
                FreightOrderStatus.HOLDED,
            },
            FreightOrderStatus.IN_PROGRESS: {
                FreightOrderStatus.COMPLETED,
                FreightOrderStatus.CANCELLED,
                FreightOrderStatus.HOLDED,
            },
            FreightOrderStatus.HOLDED: {
                FreightOrderStatus.IN_PROGRESS,
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






class FoEditFieldsView(View):
    template_name = "sales/fo_detail.html"

    def post(self, request, pk):
        order = get_object_or_404(FreightOrder, pk=pk)

        if order.status != FreightOrderStatus.DRAFT:
            messages.error(request, "Freight Order hanya bisa di-edit saat status DRAFT.")
            return redirect("sales:fo_detail", pk=order.pk)

        form = FreightOrderEditForm(request.POST, instance=order)

        if form.is_valid():
            form.save()  # ⬅ semua field (termasuk down_payment) disimpan
            messages.success(request, "Freight Order berhasil diupdate.")
            return redirect("sales:fo_detail", pk=order.pk)

        messages.error(request, f"Gagal menyimpan: {form.errors.as_text()}")
        context = {
            "order": order,
            "edit_form": form,
        }
        return render(request, self.template_name, context)

