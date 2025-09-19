from django.urls import path
from . import views

app_name = "sales"

from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path("ping/", views.ping, name="ping"),
    # Step-1 (header)
    path("freight/quotation/add/", views.quotation_add_header, name="freight_quotation_add"),
    # Step-2 (dua opsi route):
    path("freight/quotation/add/<int:pk>/lines/", views.quotation_add_lines, name="freight_quotation_add_lines"),
   # path("freight/quotation/lines/", views.quotation_add_lines_session, name="freight_quotation_add_lines_session"),
    path("freight/quotation/lines/", views.quotation_add_lines_manual_session, name="freight_quotation_add_lines_session"),
 
    # List
    path("freight/quotation/list/", views.freight_quotation_list, name="freight_quotation_list"),
    # Debug (biar mgmt command gak error)
    path("debug/", views.debug_status, name="debug_status"),
]

  
