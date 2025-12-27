import csv
import io
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse
from django.views.generic import ListView, CreateView, FormView

from accounting.models.chart import Account
from accounting.forms.accounts import AccountForm, AccountImportForm
from django.http import HttpResponse
from django.utils import timezone
from django.views import View

from django.views.generic import TemplateView

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from accounting.models.chart import Account
from django.views.generic import DetailView, UpdateView  # ← INI YANG KURANG
from accounting.models.settings import AccountingSettings
from accounting.services.account import account_is_used




class AccountListView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        active_year = AccountingSettings.get_active_year()

        qs = (
            Account.objects
            .filter(chart_year=active_year)
            .select_related("parent")
            .order_by("type", "code")
        )

        # ambil type yang benar-benar ada di DB
        db_types = list(qs.values_list("type", flat=True).distinct())

        # label map dari TYPE_CHOICES (kalau match)
        type_labels = dict(Account.TYPE_CHOICES)

        # bikin groups berdasarkan urutan DB (atau sort kalau mau)
        groups = []
        for t in db_types:
            items = list(qs.filter(type=t))
            if items:
                groups.append((t, type_labels.get(t, t), items))

        ctx["groups"] = groups
        ctx["coa_count"] = qs.count()

        # debug helper (boleh hapus nanti)
        ctx["db_types"] = db_types[:10]
        return ctx
    
class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = "accounts/form.html"

    def get_success_url(self):
        return reverse("accounting:account_list")



def _to_bool(v, default=True):
    if v is None:
        return default
    s = str(v).strip().lower()
    if s == "":
        return default
    return s in ("1", "true", "yes", "y", "on")


class AccountTreeView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/tree.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        qs = (
            Account.objects
            .select_related("parent")
            .prefetch_related("children")
            .order_by("code")
        )

        # optional filter type (kalau mau)
        acc_type = self.request.GET.get("type")
        if acc_type:
            qs = qs.filter(type=acc_type)

        roots = qs.filter(parent__isnull=True)

        ctx["roots"] = roots
        ctx["types"] = Account.TYPE_CHOICES
        ctx["current_type"] = acc_type or ""
        return ctx


class AccountDetailView(LoginRequiredMixin, DetailView):
    model = Account
    template_name = "accounts/detail.html"
    context_object_name = "acc"

    def get_queryset(self):
        return (
            Account.objects
            .select_related("parent")
            .prefetch_related("children")
        )


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = "accounts/form.html"
    context_object_name = "acc"

    def get_queryset(self):
        return Account.objects.select_related("parent")

    def get_success_url(self):
        return reverse("accounting:account_detail", kwargs={"pk": self.object.pk})


class AccountExportCsvView(LoginRequiredMixin, View):
    def get(self, request):
        active_year = AccountingSettings.get_active_year()

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="coa_export.csv"'
        resp.write("\ufeff")  # UTF-8 BOM (Excel)

        w = csv.writer(resp, delimiter=";", lineterminator="\n")
        w.writerow([
            "chart_year",
            "code",
            "name",
            "type",
            "parent_code",
            "is_postable",
            "is_active",
        ])

        qs = (
            Account.objects
            .select_related("parent")
            .filter(chart_year=active_year)
            .order_by("code")
        )

        for a in qs:
            w.writerow([
                a.chart_year,
                a.code,
                a.name,
                a.type,
                a.parent.code if a.parent else "",
                "1" if a.is_postable else "0",
                "1" if a.is_active else "0",
            ])

        return resp

class AccountImportView(LoginRequiredMixin, FormView):
    template_name = "accounts/import.html"  # sesuaikan
    form_class = AccountImportForm

    def _account_is_used(self, acc: Account) -> bool:
        return JournalLine.objects.filter(account=acc).exists()

    @transaction.atomic
    def form_valid(self, form):
        f = form.cleaned_data["file"]
        raw = f.read()

        # ✅ ambil flag overwrite dari form (kalau field ada)
        overwrite_existing = bool(form.cleaned_data.get("overwrite_existing", False))

        # decode (support utf-8-sig utk BOM Excel)
        text = None
        for enc in ("utf-8-sig", "utf-8", "cp1252"):
            try:
                text = raw.decode(enc)
                break
            except Exception:
                pass
        if text is None:
            messages.error(self.request, "File tidak bisa dibaca (encoding). Simpan CSV sebagai UTF-8.")
            return self.form_invalid(form)

        # detect delimiter ; atau ,
        try:
            sample = text[:4096]
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ";"

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)

        headers = set([c.strip() for c in (reader.fieldnames or [])])
        required = {"code", "name", "type"}
        if not required.issubset(headers):
            messages.error(
                self.request,
                "Header CSV minimal: code,name,type. Optional: chart_year,parent_code,is_postable,is_active"
            )
            return self.form_invalid(form)

        active_year = AccountingSettings.get_active_year()

        def _bool(v, default=True):
            if v is None or str(v).strip() == "":
                return default
            s = str(v).strip().lower()
            return s in ("1", "true", "yes", "y", "on")

        def _int_or_none(v):
            if v is None:
                return None
            s = str(v).strip()
            return int(s) if s.isdigit() else None

        rows = []
        for row in reader:
            code = (row.get("code") or "").strip()
            name = (row.get("name") or "").strip()
            typ = (row.get("type") or "").strip()
            parent_code = (row.get("parent_code") or "").strip()

            if not code or not name or not typ:
                continue

            chart_year = _int_or_none(row.get("chart_year")) or active_year

            rows.append({
                "chart_year": chart_year,
                "code": code,
                "name": name,
                "type": typ,
                "parent_code": parent_code,
                "is_active": _bool(row.get("is_active"), default=True),
                "is_postable": _bool(row.get("is_postable"), default=True),
            })

        if not rows:
            messages.warning(self.request, "Tidak ada baris valid untuk diimport.")
            return self.form_invalid(form)

        created, updated, skipped = 0, 0, 0

        # PASS 1: create/update semua akun tanpa parent
        # - overwrite_existing OFF: jika sudah ada -> skip
        # - overwrite_existing ON : jika sudah ada -> update (tapi BLOCK kalau sudah dipakai journal)
        for r in rows:
            obj = Account.objects.filter(
                chart_year=r["chart_year"],
                code=r["code"],
            ).first()

            if obj:
                if not overwrite_existing:
                    skipped += 1
                    continue

                # ✅ GUARD: sudah dipakai journal? -> abort (rollback)
                if self._account_is_used(obj):
                    form.add_error(
                        None,
                        f"Account {obj.code} ({obj.name}) sudah dipakai journal. "
                        "Overwrite tidak diizinkan untuk menjaga histori akunting."
                    )
                    # rollback karena atomic
                    return self.form_invalid(form)

                # overwrite allowed
                obj.name = r["name"]
                obj.type = r["type"]
                obj.is_active = r["is_active"]
                obj.is_postable = r["is_postable"]
                obj.save()
                updated += 1
            else:
                Account.objects.create(
                    chart_year=r["chart_year"],
                    code=r["code"],
                    name=r["name"],
                    type=r["type"],
                    is_active=r["is_active"],
                    is_postable=r["is_postable"],
                )
                created += 1

        # map lookup cepat per (chart_year, code)
        years = {r["chart_year"] for r in rows}
        codes = {r["code"] for r in rows} | {r["parent_code"] for r in rows if r["parent_code"]}

        acc_map = {
            (a.chart_year, a.code): a
            for a in Account.objects.filter(chart_year__in=years, code__in=codes)
        }

        # PASS 2: set parent (parent harus di chart_year yg sama)
        parent_set, parent_skip = 0, 0
        for r in rows:
            pcode = r["parent_code"]
            if not pcode:
                continue

            child = acc_map.get((r["chart_year"], r["code"]))
            parent = acc_map.get((r["chart_year"], pcode))

            if not child or not parent or child.code == parent.code:
                parent_skip += 1
                continue

            if child.parent_id != parent.id:
                child.parent = parent
                child.save(update_fields=["parent"])

            parent_set += 1

        messages.success(
            self.request,
            "Import COA selesai. "
            f"created={created}, updated={updated}, skipped={skipped}, "
            f"parent_set={parent_set}, parent_skip={parent_skip}. "
            f"overwrite_existing={'ON' if overwrite_existing else 'OFF'}. Active FY={active_year}."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("accounting:account_list")  # sesuaikan
