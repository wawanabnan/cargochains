# projects/views/costs.py
from datetime import datetime
from urllib.parse import urlencode

from django.db.models import Q
from django.views.generic import ListView

from ..models import ProjectCost, CostCategory, Project
# projects/views/costs.py (tambahkan)
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from django.http import JsonResponse, HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required

from ..forms import ProjectCostForm

from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView

from ..models import ProjectCost
from ..forms import ProjectCostForm



def _parse_date(s: str):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _count_selected_filters(request):
    n = 0
    n += len([x for x in request.GET.getlist("project") if x.isdigit()])
    n += len([x for x in request.GET.getlist("category") if x.isdigit()])
    if (request.GET.get("ccy") or "").strip(): n += 1
    if (request.GET.get("date_from") or "").strip(): n += 1
    if (request.GET.get("date_to") or "").strip():   n += 1
    if (request.GET.get("amin") or "").strip():      n += 1
    if (request.GET.get("amax") or "").strip():      n += 1
    if (request.GET.get("has_attach") or "") == "1": n += 1
    return n


@login_required
@require_POST
def project_cost_bulk(request):
    ids = [int(x) for x in request.POST.getlist("ids") if x.isdigit()]
    action = (request.POST.get("action") or "").lower()
    if not ids:
        messages.warning(request, "No rows selected.")
        return redirect(request.META.get("HTTP_REFERER", "projects:cost_list"))

    qs = ProjectCost.objects.filter(pk__in=ids)

    if action == "delete":
        n = qs.count()
        qs.delete()
        messages.success(request, f"Deleted {n} cost(s).")
    elif action == "print":
        # TODO: implement print/export
        messages.info(request, f"Ready to print {qs.count()} cost(s).")
    else:
        messages.error(request, "Unknown action.")
    return redirect(request.META.get("HTTP_REFERER", "projects:cost_list"))

class ProjectCostListView(ListView):
    model = ProjectCost
    template_name = "projects/cost_list.html"
    context_object_name = "costs"
    paginate_by = 10
    ordering = ["-cost_date", "-created_at"]

    def get_queryset(self):
        qs = (
            ProjectCost.objects
            .select_related("project", "category")
        )

        # search (judul / ref / project number / category name / notes)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(ref__icontains=q) |
                Q(notes__icontains=q) |
                Q(project__number__icontains=q) |
                Q(project__name__icontains=q) |
                Q(category__name__icontains=q)
            )

        # filters
        flt_projects  = [int(x) for x in self.request.GET.getlist("project") if x.isdigit()]
        flt_categories= [int(x) for x in self.request.GET.getlist("category") if x.isdigit()]
        flt_ccy       = (self.request.GET.get("ccy") or "").strip().upper()
        date_from     = _parse_date(self.request.GET.get("date_from"))
        date_to       = _parse_date(self.request.GET.get("date_to"))
        amin_raw      = (self.request.GET.get("amin") or "").replace(",", "").strip()
        amax_raw      = (self.request.GET.get("amax") or "").replace(",", "").strip()
        has_attach    = (self.request.GET.get("has_attach") or "") == "1"

        if flt_projects:
            qs = qs.filter(project_id__in=flt_projects)
        if flt_categories:
            qs = qs.filter(category_id__in=flt_categories)
        if flt_ccy:
            qs = qs.filter(currency_code__iexact=flt_ccy)
        if date_from:
            qs = qs.filter(cost_date__gte=date_from)
        if date_to:
            qs = qs.filter(cost_date__lte=date_to)
        if amin_raw:
            try:
                qs = qs.filter(amount__gte=float(amin_raw))
            except ValueError:
                pass
        if amax_raw:
            try:
                qs = qs.filter(amount__lte=float(amax_raw))
            except ValueError:
                pass
        if has_attach:
            qs = qs.exclude(attachment="").exclude(attachment__isnull=True)

        # sorting
        sort = (self.request.GET.get("sort") or "").strip()
        direction = (self.request.GET.get("dir") or "desc").lower()
        sort_map = {
            "date": "cost_date",
            "created": "created_at",
            "project": "project__number",
            "category": "category__name",
            "title": "title",
            "amount": "amount",
            "ccy": "currency_code",
        }
        if sort in sort_map:
            prefix = "" if direction == "asc" else "-"
            qs = qs.order_by(prefix + sort_map[sort])
        else:
            qs = qs.order_by(*self.ordering)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.request.GET.copy()
        qs.pop("page", None)
        base_qs = urlencode(qs, doseq=True)

        projects   = list(Project.objects.all().order_by("-created_at").only("id", "number", "name"))
        categories = list(CostCategory.objects.all().order_by("name"))
        # ambil distinct currency dari data yang ada
        currencies = (
            ProjectCost.objects
            .values_list("currency_code", flat=True)
            .distinct()
            .order_by("currency_code")
        )

        ctx.update({
            "title": "Project Costs",
            "q": self.request.GET.get("q", ""),
            "sort": self.request.GET.get("sort", ""),
            "dir": self.request.GET.get("dir", "desc"),
            "base_qs": base_qs,

            "projects": projects,
            "categories": categories,
            "currencies": currencies,

            "flt_projects": [int(x) for x in self.request.GET.getlist("project") if x.isdigit()],
            "flt_categories": [int(x) for x in self.request.GET.getlist("category") if x.isdigit()],
            "flt_ccy": (self.request.GET.get("ccy") or "").upper(),
            "date_from": self.request.GET.get("date_from", ""),
            "date_to": self.request.GET.get("date_to", ""),
            "amin": self.request.GET.get("amin", ""),
            "amax": self.request.GET.get("amax", ""),
            "has_attach": (self.request.GET.get("has_attach") or "") == "1",

            "filters_count": _count_selected_filters(self.request),
        })
        return ctx


# projects/views/costs.py

class ProjectCostCreateView(LoginRequiredMixin, CreateView):
    model = ProjectCost
    form_class = ProjectCostForm
    template_name = "projects/cost_form.html"   # fallback full-page
    success_url = reverse_lazy("projects:cost_list")

    def form_valid(self, form):
        obj = form.save()
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "id": obj.id})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        return super().form_invalid(form)



@login_required
@require_POST
def project_cost_add(request):
    form = ProjectCostForm(request.POST, request.FILES)
    if form.is_valid():
        obj = form.save()
        # jika AJAX → balas JSON; kalau bukan → redirect
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "id": obj.id})
        messages.success(request, "Project cost created.")
        return redirect("projects:cost_list")
    # invalid
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    messages.error(request, "Please fix the errors.")
    return redirect("projects:cost_list")
