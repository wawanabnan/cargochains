from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q
from django.utils.decorators import method_decorator

from account.decorators import role_required
from ..models import SalesQuotation,SalesOrder
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth import REDIRECT_FIELD_NAME  # default: "next"
from ..auth import SalesAccessRequiredMixin


@method_decorator(login_required(login_url="account:login",
                                 redirect_field_name=REDIRECT_FIELD_NAME), name="dispatch")
@method_decorator(role_required("sales", "admin"), name="dispatch")  # kalau kamu pakai role
class QuotationListView(LoginRequiredMixin, ListView):
    login_url = "account:login"
    model = SalesQuotation
    template_name = "freight/quotation_list.html"
    context_object_name = "quotations"            # samakan dgn variabel di template
    paginate_by = 25                              # ubah sesuai kebutuhan
    ordering = ["-created_at"]                    # sesuaikan field waktu milikmu

    def get_queryset(self):
        qs = super().get_queryset()
        # contoh optimisasi relasi jika ada:
        # qs = qs.select_related("customer")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            # SESUAIKAN field pencarian dengan skema kamu
            # Minimal cari di 'number'; kalau ada relasi customer/name dan status, ini ikut kepake
            qs = qs.filter(
                Q(number__icontains=q) |
                Q(status__icontains=q) |
                Q(customer__name__icontains=q)
            )
        # Sorting opsional via ?sort=number / created_at & ?dir=asc|desc
        sort = (self.request.GET.get("sort") or "").strip()
        direction = (self.request.GET.get("dir") or "desc").lower()
        allowed = {"number", "created_at", "status"}  # tambahkan field yang aman untuk di-sort
        if sort in allowed:
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + sort)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "Freight Quotations",
            "ns": "sales",            # kalau dipakai utk active menu
            "menu": "quotation",
            "q": self.request.GET.get("q", ""),
            "sort": self.request.GET.get("sort", ""),
            "dir": self.request.GET.get("dir", "desc"),
        })
        return ctx


@method_decorator(login_required(login_url="account:login"), name="dispatch")   # ⬅️ ini HARUS di atas
@method_decorator(role_required("sales", "admin"), name="dispatch")
class OrderListView(LoginRequiredMixin, ListView):
    login_url = "account:login"
    model = SalesOrder                     # ⬅️ ganti jika nama beda
    template_name = "freight/order_list.html"   # ⬅️ pastikan file ada
    context_object_name = "orders"         # ⬅️ plural untuk list
    paginate_by = 25
    ordering = ["-created_at"]             # ⬅️ sesuaikan field waktu

    def get_queryset(self):
        qs = super().get_queryset()
        # contoh optimisasi: qs = qs.select_related("customer")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(number__icontains=q) |
                Q(status__icontains=q) |
                Q(customer__name__icontains=q)
            )
        # optional sort
        sort = (self.request.GET.get("sort") or "").strip()
        direction = (self.request.GET.get("dir") or "desc").lower()
        allowed = {"number", "created_at", "status"}
        if sort in allowed:
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + sort)
        return qs
