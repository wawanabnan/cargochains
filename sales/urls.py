# sales/urls.py
from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required

# CBV: Lists & Details
from .views.lists import QuotationListView, OrderListView
from .views.details import QuotationDetailView, OrderDetailView

# FBV: Add / Edit / Print / PDF / Actions
#from .views.adds import quotation_add_header, quotation_add_lines
from .views.adds import FreightQuotationAddView  # ⬅️ ganti ini
from .views.edits import FreightQuotationEditView 
from .views.prints import quotation_print, quotation_pdf, order_print, order_pdf
from .views.actions import (
    quotation_change_status, order_change_status, quotation_generate_so
)



from .auth import sales_access_required
from .views import actions as action_views


app_name = "sales"

urlpatterns = [
    # ===== QUOTATIONS =====
    path("freight/quotations/",                      QuotationListView.as_view(),   name="quotation_list"),
    path("freight/quotations/<int:pk>/",             QuotationDetailView.as_view(), name="quotation_details"),  # ← pakai nama plural 'details'
 
    path("freight/quotations/add/",               FreightQuotationAddView.as_view(),  name="quotation_add"),
    path("freight/quotations/<int:pk>/edit/",     FreightQuotationEditView.as_view(),  name="quotation_edit"),


   # path("freight/quotations/lines/",                login_required(quotation_add_lines,  login_url="account:login"), name="quotation_add_lines"),
   
    path("freight/quotations/<int:pk>/status/",      login_required(quotation_change_status, login_url="account:login"), name="quotation_change_status"),
    path("freight/quotations/<int:pk>/generate-so/", login_required(quotation_generate_so,  login_url="account:login"), name="quotation_generate_so"),
    path("freight/quotations/<int:pk>/print/",       login_required(quotation_print,      login_url="account:login"), name="quotation_print"),
    path("freight/quotations/<int:pk>/pdf/",         login_required(quotation_pdf,        login_url="account:login"), name="quotation_pdf"),

    # ===== ORDERS =====
    path("freight/orders/",                          OrderListView.as_view(),       name="order_list"),
    path("freight/orders/<int:pk>/",                 OrderDetailView.as_view(),     name="order_details"),     # ← pakai nama plural 'details'
    path("freight/orders/<int:pk>/status/",          login_required(order_change_status,   login_url="account:login"), name="order_change_status"),
    path("freight/orders/<int:pk>/print/",           login_required(order_print,    login_url="account:login"),      name="order_print"),
    path("freight/orders/<int:pk>/pdf/",             login_required(order_pdf,      login_url="account:login"),      name="order_pdf"),

    # ===== LEGACY ALIASES (biar reverse lama '..._detail' tetap hidup) =====
    path("freight/quotations/<int:pk>/",             QuotationDetailView.as_view(), name="quotation_detail"),
    path("freight/orders/<int:pk>/",                 OrderDetailView.as_view(),     name="order_detail"),

    # ===== LEGACY REDIRECTS (singular → plural) =====
    path("freight/quotation/",                       RedirectView.as_view(pattern_name="sales:quotation_list",  permanent=False)),
    path("freight/quotation/<int:pk>/",              RedirectView.as_view(pattern_name="sales:quotation_details", permanent=False)),
    path("freight/order/",                           RedirectView.as_view(pattern_name="sales:order_list",       permanent=False)),
    path("freight/order/<int:pk>/",                  RedirectView.as_view(pattern_name="sales:order_details",     permanent=False)),
    path("freight/quotation/add/",                   RedirectView.as_view(pattern_name="sales:quotation_add",     permanent=False)),
    path("freight/quotation/lines/",                 RedirectView.as_view(pattern_name="sales:quotation_add_lines", permanent=False)),

    #path("freight/quotations/<int:pk>/generate-so/", sales_access_required(quotation_generate_so), name="quotation_generate_so"),
    #path("freight/orders/<int:pk>/status/", action_views.order_set_status, name="order_set_status"),
   

]






