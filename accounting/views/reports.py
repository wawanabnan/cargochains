from datetime import date
from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils.dateparse import parse_date
from django.views.generic import TemplateView

from accounting.models.chart import Account
from accounting.models.journal import JournalLine  # sesuaikan kalau path beda


class TrialBalanceView(LoginRequiredMixin, TemplateView):
    template_name = "reports/trial_balance.html"

    def _get_date(self, key, default=None):
        s = (self.request.GET.get(key) or "").strip()
        if not s:
            return default
        d = parse_date(s)  # YYYY-MM-DD
        return d or default

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        today = date.today()
        date_from = self._get_date("from", default=today.replace(day=1))
        date_to = self._get_date("to", default=today)

        # ---- Base queryset journal lines ----
        q = JournalLine.objects.select_related("account", "journal")

        # posted only (kalau field ada)
        posted_only = False
        try:
            q = q.filter(journal__status="posted")
            posted_only = True
        except Exception:
            posted_only = False

        # filter tanggal journal (sesuaikan jika fieldnya beda)
        q = q.filter(journal__date__gte=date_from, journal__date__lte=date_to)

        # ---- Aggregate per account (leaf) ----
        agg = (
            q.values("account_id")
             .annotate(debit=Sum("debit"), credit=Sum("credit"))
        )

        leaf_amounts = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})
        for r in agg:
            aid = r["account_id"]
            leaf_amounts[aid]["debit"] = r["debit"] or Decimal("0.00")
            leaf_amounts[aid]["credit"] = r["credit"] or Decimal("0.00")

        # ---- Load accounts & build tree ----
        accounts = list(
            Account.objects
            .select_related("parent")
            .prefetch_related("children")
            .all()
            .order_by("code")
        )

        children_map = defaultdict(list)
        roots = []
        for a in accounts:
            if a.parent_id:
                children_map[a.parent_id].append(a)
            else:
                roots.append(a)

        for pid in children_map:
            children_map[pid].sort(key=lambda x: x.code)
        roots.sort(key=lambda x: x.code)

        # ---- Roll-up parent from children ----
        rolled = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})

        def dfs(a: Account):
            d = leaf_amounts[a.id]["debit"] if a.id in leaf_amounts else Decimal("0.00")
            c = leaf_amounts[a.id]["credit"] if a.id in leaf_amounts else Decimal("0.00")
            for ch in children_map.get(a.id, []):
                cd, cc = dfs(ch)
                d += cd
                c += cc
            rolled[a.id]["debit"] = d
            rolled[a.id]["credit"] = c
            return d, c

        for r in roots:
            dfs(r)

        # ---- Build rows per type with indentation ----
        type_labels = dict(Account.TYPE_CHOICES)
        type_order = [k for k, _ in Account.TYPE_CHOICES]

        rows_by_type = defaultdict(list)

        def build_rows(node: Account, level: int):
            d = rolled[node.id]["debit"]
            c = rolled[node.id]["credit"]
            rows_by_type[node.type].append({
                "account_id": node.id,          # ⬅️ WAJIB
                "code": node.code,
                "name": node.name,
                "level": level,
                "is_postable": node.is_postable,
                "debit": d,
                "credit": c,
                "balance": d - c,
            })

            for ch in children_map.get(node.id, []):
                build_rows(ch, level + 1)

        for r in roots:
            build_rows(r, 0)

        # ---- Sections list (untuk template, no dict tricks) ----
        sections = []
        for t in type_order:
            rows = rows_by_type.get(t, [])
            if rows:
                sections.append({
                    "type": t,
                    "label": type_labels.get(t, t),
                    "rows": rows,
                })

        # ---- Totals (hitung dari roots biar tidak double count) ----
        total_debit = sum((rolled[r.id]["debit"] for r in roots), Decimal("0.00"))
        total_credit = sum((rolled[r.id]["credit"] for r in roots), Decimal("0.00"))
        diff = total_debit - total_credit

        ctx.update({
            "date_from": date_from,
            "date_to": date_to,
            "posted_only": posted_only,
            "sections": sections,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "diff": diff,
        })
        return ctx


class GeneralLedgerView(LoginRequiredMixin, TemplateView):
    template_name = "reports/general_ledger.html"

    def _get_date(self, key, default=None):
        s = (self.request.GET.get(key) or "").strip()
        if not s:
            return default
        d = parse_date(s)  # YYYY-MM-DD
        return d or default

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        account = Account.objects.get(pk=kwargs["account_id"])

        today = date.today()
        date_from = self._get_date("from", default=today.replace(day=1))
        date_to = self._get_date("to", default=today)

        q = JournalLine.objects.select_related("journal").filter(account=account)

        # posted only jika ada
        posted_only = False
        try:
            q = q.filter(journal__status="posted")
            posted_only = True
        except Exception:
            posted_only = False

        # opening balance (sebelum periode)
        open_q = q.filter(journal__date__lt=date_from)
        open_agg = open_q.aggregate(
            debit=Sum("debit"),
            credit=Sum("credit"),
        )
        opening_balance = (open_agg["debit"] or Decimal("0.00")) - (open_agg["credit"] or Decimal("0.00"))

        # transaksi periode
        lines = (
            q.filter(journal__date__gte=date_from, journal__date__lte=date_to)
             .order_by("journal__date", "journal__id", "id")
        )

        rows = []
        running = opening_balance
        for ln in lines:
            running += (ln.debit or Decimal("0.00")) - (ln.credit or Decimal("0.00"))
            rows.append({
                "date": ln.journal.date,
                "ref": getattr(ln.journal, "number", ln.journal_id),
                "desc": getattr(ln, "label", ""),
                "debit": ln.debit or Decimal("0.00"),
                "credit": ln.credit or Decimal("0.00"),
                "balance": running,
            })

        ctx.update({
            "account": account,
            "date_from": date_from,
            "date_to": date_to,
            "posted_only": posted_only,
            "opening_balance": opening_balance,
            "rows": rows,
        })
        return ctx
