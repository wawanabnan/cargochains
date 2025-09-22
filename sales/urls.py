# sales/urls.py
from django.urls import path
from django.views.generic import RedirectView
from . import views
from .views.actions import quotation_generate_so  # ⟵ tambahkan baris ini

app_name = "sales"

urlpatterns = [
    # INDEX / LIST (baru, tanpa /list/)
    path("freight/quotation/", views.quotation_list, name="quotation_list"),

    # (opsional) keep old URL → redirect ke yang baru
    path(
        "freight/quotation/list/",
        RedirectView.as_view(pattern_name="sales:quotation_list", permanent=False),
        name="quotation_list_legacy",
    ),

    # add
    path("freight/quotation/add/", views.quotation_add_header, name="quotation_add"),
    path("freight/quotation/lines/", views.quotation_add_lines, name="quotation_add_lines"),

    # detail & edit
    path("freight/quotation/<int:pk>/", views.quotation_detail, name="quotation_detail"),
    path("freight/quotation/<int:pk>/edit/", views.quotation_edit, name="quotation_edit"),

    # actions (sudah OK, tetap sejajar)
    path("freight/quotation/<int:pk>/change-status/", views.quotation_change_status, name="quotation_change_status"),
    path("freight/quotation/<int:pk>/delete/", views.quotation_delete, name="quotation_delete"),
    
   
    path("freight/quotation/<int:pk>/generate-so/", views.quotation_generate_so, name="quotation_generate_so"), 
    #name yang dipanggil di template
    
   
    # Orders
    path("freight/orders/", views.order_list, name="order_list"),
    path("freight/orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("freight/orders/<int:pk>/change-status/", views.order_change_status, name="order_change_status"),


    # detail/print/pdf
    path("freight/quotation/<int:pk>/print/", views.quotation_print, name="quotation_print"),
    path("freight/quotation/<int:pk>/pdf/",   views.quotation_pdf,   name="quotation_pdf"),


    # Sales Order: print & pdf
    path("freight/orders/<int:pk>/print/", views.order_print, name="order_print"),
    path("freight/orders/<int:pk>/pdf/",   views.order_pdf,   name="order_pdf"),


]
