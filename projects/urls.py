
from django.urls import path
from . import views
from  .views.costs import ProjectCostListView, project_cost_bulk, ProjectCostCreateView
from  .views.projects import ProjectListView, ProjectCreateView, ProjectUpdateView, ProjectCostCreateGlobalView


app_name = "projects"

urlpatterns = [
    path("", ProjectListView.as_view(), name="project_list"),
    path("add/", ProjectCreateView.as_view(), name="project_add"),
    path("<int:pk>/edit/", ProjectUpdateView.as_view(), name="project_edit"),
    path("costs/", ProjectCostListView.as_view(), name="cost_list"),
    path("costs/bulk/", project_cost_bulk, name="cost_bulk"),
    #path("costs/add/", project_cost_add, name="cost_add"), 
    path("costs/add/", ProjectCostCreateView.as_view(), name="cost_add"),   # ← GET+POS
]
            
    #path("add/", views.ProjectCreateView.as_view(), name="project_add"),
   # path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_edit"),
  #  path("<int:project_pk>/costs/add/", views.ProjectCostCreateView.as_view(), name="cost_add_project"),
   # path("costs/<int:pk>/edit/", views.ProjectCostUpdateView.as_view(), name="cost_edit"),
    #path("", views.ProjectListView.as_view(), name="project_list"),

     # ADD (global & by-project)
    
   # path("<int:project_pk>/costs/add/", views.ProjectCostCreateView.as_view(), name="project_cost_add"),
   # path("costs/<int:pk>/edit/", views.ProjectCostUpdateView.as_view(), name="cost_edit"),
