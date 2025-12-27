from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, View

from accounting.models.journal import Journal
from accounting.services.posting import post_journal


class JournalListView(LoginRequiredMixin, ListView):
    model = Journal
    template_name = "journals/list.html"
    context_object_name = "journals"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related()
        q = (self.request.GET.get("q") or "").strip()
        posted = (self.request.GET.get("posted") or "").strip()

        if q:
            qs = qs.filter(number__icontains=q) | qs.filter(ref__icontains=q) | qs.filter(description__icontains=q)

        if posted in ("0", "1"):
            qs = qs.filter(posted=(posted == "1"))

        return qs.order_by("-date", "-id")


class JournalDetailView(LoginRequiredMixin, DetailView):
    model = Journal
    template_name = "journals/detail.html"
    context_object_name = "journal"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("lines__account")

class JournalPostView(LoginRequiredMixin, View):
    def post(self, request, pk):
        journal = get_object_or_404(Journal, pk=pk)

        try:
            post_journal(journal)
            messages.success(request, f"Journal {journal.number} berhasil di-POST (locked).")
        except ValidationError as e:
            messages.error(request, f"Gagal POST: {e}")
        except Exception as e:
            messages.error(request, f"Gagal POST: {e}")

        return redirect("accounting:journal_detail", pk=journal.pk)
