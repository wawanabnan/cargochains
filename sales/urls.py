from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    # list & add
    path("freight/quotation/list/",  views.quotation_list,        name="quotation_list"),
    path("freight/quotation/add/",   views.quotation_add_header,  name="quotation_add"),
    #path("freight/quotation/<int:pk>/lines/",  views.quotation_add_lines,  name="quotation_add_lines"),

    # step-2 lines (tanpa pk)
    path("freight/quotation/lines/", views.quotation_add_lines, name="quotation_add_lines"),

    # detail & edit
    path("freight/quotation/<int:pk>/",        views.quotation_detail,     name="quotation_detail"),
    path("freight/quotation/<int:pk>/edit/",   views.quotation_edit,       name="quotation_edit"),

    
    # (opsional) endpoint lama berbasis session → redirect saja
    #path("freight/quotation/lines/",           views.quotation_add_lines_session, name="quotation_add_lines_session"),

    # actions
    path("freight/quotation/<int:pk>/delete/", views.quotation_delete,      name="quotation_delete"),
    path("quotations/<int:pk>/change-status/", views.quotation_change_status, name="quotation_change_status"),

]
