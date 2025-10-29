from django.db.models import Sum, Value, DecimalField, Q
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, UpdateView
from django.db import transaction

from . import models as m
from .forms import ProjectForm, ProjectCostForm


class ProjectCreateView(CreateView):
    model = m.Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Project '{self.object.number}' berhasil dibuat.")
        return redirect(reverse("projects:project_edit", args=[self.object.pk]))


class ProjectUpdateView(UpdateView):
    model = m.Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Project '{self.object.number}' berhasil diperbarui.")
        return redirect(reverse("projects:project_edit", args=[self.object.pk]))


class ProjectCostCreateView(View):
    template_name = "projects/cost_form.html"

    def get(self, request, project_pk):
        project = get_object_or_404(m.Project, pk=project_pk)
        form = ProjectCostForm(project=project)
        return render(request, self.template_name, {"form": form, "project": project})

    @transaction.atomic
    def post(self, request, project_pk):
        project = get_object_or_404(m.Project, pk=project_pk)
        form = ProjectCostForm(request.POST, request.FILES, project=project)  # ⬅️ FILES
        if form.is_valid():
            cost = form.save()
            messages.success(request, f"Biaya '{cost.title}' ditambahkan.")
            return redirect(reverse("projects:project_edit", args=[project.pk]) + "#costs")
        return render(request, self.template_name, {"form": form, "project": project})


class ProjectCostUpdateView(View):
    template_name = "projects/cost_form.html"

    def get(self, request, pk):
        cost = get_object_or_404(m.ProjectCost, pk=pk)
        form = ProjectCostForm(instance=cost)
        return render(request, self.template_name, {"form": form, "project": cost.project})

    @transaction.atomic
    def post(self, request, pk):
        cost = get_object_or_404(m.ProjectCost, pk=pk)
        form = ProjectCostForm(request.POST, instance=cost)
        if form.is_valid():
            form.save()
            messages.success(request, f"Biaya '{cost.title}' diperbarui.")
            return redirect(reverse("projects:project_edit", args=[cost.project.pk]) + "#costs")
        return render(request, self.template_name, {"form": form, "project": cost.project})


from django.core.paginator import Paginator
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
# ---- Project List ----
class ProjectListView(View):
    template_name = "projects/project_list.html"

    def get(self, request):
        qs = m.Project.objects.select_related("category").annotate(
            total_cost=Coalesce(
                Sum("costs__amount"),
                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )

        # --- filters ---
        status = request.GET.get("status")
        category = request.GET.get("category")
        q = request.GET.get("q")

        if status:
            qs = qs.filter(status=status)
        if category:
            qs = qs.filter(category_id=category)
        if q:
            qs = qs.filter(models.Q(name__icontains=q) | models.Q(ref_number__icontains=q))

        # --- pagination ---
        paginator = Paginator(qs.order_by("-created_at"), 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        categories = m.ProjectCategory.objects.all().order_by("name")

        context = {
            "page_obj": page_obj,
            "categories": categories,
            "statuses": m.ProjectStatus.choices,
            "status_selected": status,
            "category_selected": category,
            "q": q or "",
        }
        return render(request, self.template_name, context)




# --- imports (tambahkan jika belum ada) ---
from django.core.paginator import Paginator
from django.db.models import Sum, Value, DecimalField, Q
from django.db.models.functions import Coalesce

# ---- LIST: ProjectCost ----
class ProjectCostListView(View):
    template_name = "projects/cost_list.html"

    def get(self, request):
        qs = m.ProjectCost.objects.select_related("project", "category")

        # filters
        q = request.GET.get("q") or ""
        project_id = request.GET.get("project") or ""
        category_id = request.GET.get("category") or ""
        dfrom = request.GET.get("date_from") or ""
        dto = request.GET.get("date_to") or ""

        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(notes__icontains=q) |
                Q(project__name__icontains=q) |
                Q(project__number__icontains=q) |
                Q(project__ref_number__icontains=q)
            )
        if project_id:
            qs = qs.filter(project_id=project_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if dfrom:
            qs = qs.filter(cost_date__gte=dfrom)
        if dto:
            qs = qs.filter(cost_date__lte=dto)

        # totals
        total_amount = qs.aggregate(
            total=Coalesce(
                Sum("amount"),
                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["total"]

        # pagination
        qs = qs.order_by("-cost_date", "-created_at")
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))

        context = {
            "page_obj": page_obj,
            "q": q, "project_selected": project_id, "category_selected": category_id,
            "date_from": dfrom, "date_to": dto,
            "projects": m.Project.objects.all().order_by("name"),
            "categories": m.CostCategory.objects.all().order_by("name"),
            "total_amount": total_amount,
        }
        return render(request, self.template_name, context)

# ---- ADD (global): ProjectCost ----
class ProjectCostCreateGlobalView(View):
    template_name = "projects/cost_form.html"

    def get(self, request):
        form = ProjectCostForm()
        return render(request, self.template_name, {"form": form, "project": None})

    def post(self, request):
        form = ProjectCostForm(request.POST, request.FILES)  # ⬅️ FILES

        if form.is_valid():
            cost = form.save()
            messages.success(request, f"Biaya '{cost.title}' ditambahkan.")
            return redirect(reverse("projects:cost_list"))
        return render(request, self.template_name, {"form": form, "project": None})
