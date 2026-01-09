from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.models.exchange_rates import ExchangeRate
from core.forms.exchange_rates import ExchangeRateForm


class ExchangeRateListView(LoginRequiredMixin, ListView):
    model = ExchangeRate
    template_name = "exchange_rates/list.html"
    context_object_name = "rows"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            ExchangeRate.objects
            .select_related("currency")
            .order_by("-rate_date", "currency__code")
        )

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(currency__code__icontains=q) |
                Q(currency__name__icontains=q) |
                Q(source__icontains=q)
            )

        d = (self.request.GET.get("date") or "").strip()
        if d:
            qs = qs.filter(rate_date=d)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["date"] = (self.request.GET.get("date") or "").strip()
        return ctx


class ExchangeRateCreateView(LoginRequiredMixin, CreateView):
    model = ExchangeRate
    form_class = ExchangeRateForm
    template_name = "exchange_rate_form.html"
    success_url = reverse_lazy("core:exchange_rate_list")

    def form_valid(self, form):
        messages.success(self.request, "Exchange rate berhasil ditambahkan.")
        return super().form_valid(form)


class ExchangeRateUpdateView(LoginRequiredMixin, UpdateView):
    model = ExchangeRate
    form_class = ExchangeRateForm
    template_name = "exchange_rates/form.html"
    success_url = reverse_lazy("core:exchange_rate_list")

    def form_valid(self, form):
        messages.success(self.request, "Exchange rate berhasil diupdate.")
        return super().form_valid(form)


class ExchangeRateDeleteView(LoginRequiredMixin, DeleteView):
    model = ExchangeRate
    template_name = "exchange_rates/confirm_delete.html"
    success_url = reverse_lazy("core:settings_exchange_rate_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Exchange rate berhasil dihapus.")
        return super().delete(request, *args, **kwargs)



from decimal import Decimal
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from core.models.currencies import Currency

class ExchangeRateLatestAPI(LoginRequiredMixin, View):

    raise_exception = True  
    def handle_no_permission(self):
        return JsonResponse(
            {"ok": False, "error": "authentication required"},
            status=401
        )

    def get(self, request):
        currency_id = request.GET.get("currency_id")
        code = (request.GET.get("code") or "").strip().upper()

        # ✅ prioritas: currency_id (lebih aman)
        cur = None
        if currency_id:
            cur = Currency.objects.filter(pk=currency_id).first()
        elif code:
            cur = Currency.objects.filter(code__iexact=code).first()
        else:
            return JsonResponse({"ok": False, "error": "currency_id or code required"}, status=400)

        if not cur:
            return JsonResponse({"ok": False, "error": "currency not found"}, status=404)

        if cur.code.upper() == "IDR":
            return JsonResponse({"ok": True, "code": "IDR", "rate_to_idr": "1.000000"})

        row = (
            ExchangeRate.objects
            .filter(currency=cur, is_active=True)
            .order_by("-rate_date", "-id")
            .first()
        )
        if not row:
            return JsonResponse({"ok": False, "error": "rate not found"}, status=404)

        return JsonResponse({
            "ok": True,
            "code": cur.code,
            "rate_to_idr": f"{Decimal(str(row.rate_to_idr)):.6f}",
            "rate_date": row.rate_date.isoformat(),
        })


import re
import time
import requests
from decimal import Decimal
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from core.models.currencies import Currency
from core.models.exchange_rates import ExchangeRate
from bs4 import BeautifulSoup

class PullBIExchangeRateView(LoginRequiredMixin, View):
    raise_exception = True
    BI_URL = "https://www.bi.go.id/id/statistik/informasi-kurs/transaksi-bi/default.aspx"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "close",
    }

    LINE_RE = re.compile(
        r"^(?P<code>[A-Z]{3})\s+(?P<nilai>\d+)\s+(?P<jual>[\d\.\,]+)\s+(?P<beli>[\d\.\,]+)"
    )

    def _fetch_bi_html(self, tries=3):
        last = None
        for i in range(tries):
            try:
                r = requests.get(
                    self.BI_URL,
                    headers=self.HEADERS,
                    timeout=30,
                )
                r.raise_for_status()
                return r.text
            except Exception as e:
                last = e
                time.sleep(1.5 * (i + 1))
        raise last

    @staticmethod
    def _to_decimal_id(s):
        # "16.845,81" -> Decimal("16845.81")
        return Decimal(s.replace(".", "").replace(",", "."))




    def post(self, request):
        today = timezone.localdate()

        try:
            html = self._fetch_bi_html()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text("\n")

            pattern = re.compile(
                r"\b(?P<code>[A-Z]{3})\b\s+"
                r"(?P<nilai>\d+)\s+"
                r"(?P<jual>[\d\.\,]+)\s+"
                r"(?P<beli>[\d\.\,]+)"
            )

            saved = []
            skipped = []

            for m in pattern.finditer(text):
                code = m.group("code").upper()
                nilai = Decimal(m.group("nilai"))
                jual = self._to_decimal_id(m.group("jual"))
                beli = self._to_decimal_id(m.group("beli"))

                rate = (jual + beli) / Decimal("2")
                if nilai > 0:
                    rate = rate / nilai

                cur = Currency.objects.filter(code=code).first()
                if not cur:
                    skipped.append(code)
                    continue

                ExchangeRate.objects.update_or_create(
                    currency=cur,
                    rate_date=today,
                    defaults={
                        "rate_to_idr": rate.quantize(Decimal("0.000001")),
                        "source": "BI",
                        "is_active": False,
                    },
                )

                if code not in saved:
                    saved.append(code)

            return JsonResponse({
                "ok": True,
                "date": today.isoformat(),
                "count": len(saved),
                "codes": saved,
                "skipped": skipped,
            })

        except Exception as e:
            return JsonResponse(
                {"ok": False, "error": str(e)},
                status=500
            )

from django.shortcuts import get_object_or_404, redirect

class ExchangeRateActivateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        obj = get_object_or_404(ExchangeRate, pk=pk)

        ExchangeRate.objects.filter(
            currency=obj.currency,
            rate_date=obj.rate_date
        ).update(is_active=False)

        obj.is_active = True
        obj.save(update_fields=["is_active"])

        messages.success(request, f"Rate {obj.currency.code} {obj.rate_date} diaktifkan.")
        return redirect("core:exchange_rate_list")


