
from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    path("add/", views.ProjectCreateView.as_view(), name="project_add"),
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_edit"),
    path("<int:project_pk>/costs/add/", views.ProjectCostCreateView.as_view(), name="cost_add"),
    path("costs/<int:pk>/edit/", views.ProjectCostUpdateView.as_view(), name="cost_edit"),
    path("", views.ProjectListView.as_view(), name="project_list"),

     # ADD (global & by-project)
    path("costs/add/", views.ProjectCostCreateGlobalView.as_view(), name="cost_add_global"),
    path("<int:project_pk>/costs/add/", views.ProjectCostCreateView.as_view(), name="cost_add"),
    path("costs/<int:pk>/edit/", views.ProjectCostUpdateView.as_view(), name="cost_edit"),
        path("costs/", views.ProjectCostListView.as_view(), name="cost_list"),



]
