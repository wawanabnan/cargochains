from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.models.number_sequences import NumberSequence  # sesuaikan path
from core.forms.number_sequences import NumberSequenceForm


def _preview(obj: NumberSequence) -> str:
    now = timezone.localdate()
    seq_next = (obj.last_number or 0) + 1
    try:
        return (obj.format or "").format(
            prefix=obj.prefix or "",
            year=now.year,
            month=now.month,
            day=now.day,
            seq=seq_next,
        )
    except Exception:
        return ""


class NumberSequenceListView(LoginRequiredMixin, ListView):
    model = NumberSequence
    template_name = "number_sequences/list.html"
    context_object_name = "rows"
    paginate_by = 25

    def get_queryset(self):
        qs = NumberSequence.objects.all().order_by("app_label", "code")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(app_label__icontains=q) |
                Q(code__icontains=q) |
                Q(prefix__icontains=q) |
                Q(name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        return ctx


class NumberSequenceCreateView(LoginRequiredMixin, CreateView):
    model = NumberSequence
    form_class = NumberSequenceForm
    template_name = "number_sequences/form.html"
    success_url = reverse_lazy("core:numbering_list")

    def get_initial(self):
        initial = super().get_initial()
        # default preview kosong
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Number sequence berhasil ditambahkan.")
        return super().form_valid(form)


class NumberSequenceUpdateView(LoginRequiredMixin, UpdateView):
    model = NumberSequence
    form_class = NumberSequenceForm
    template_name = "number_sequences/form.html"
    success_url = reverse_lazy("core:numbering_list")

    def get_initial(self):
        initial = super().get_initial()
        initial["preview"] = _preview(self.get_object())
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Number sequence berhasil diupdate.")
        return super().form_valid(form)


class NumberSequenceDeleteView(LoginRequiredMixin, DeleteView):
    model = NumberSequence
    template_name = "number_sequences/confirm_delete.html"
    success_url = reverse_lazy("core:numbering_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Number sequence berhasil dihapus.")
        return super().delete(request, *args, **kwargs)
