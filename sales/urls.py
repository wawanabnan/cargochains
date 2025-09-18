from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path("ping/", views.ping, name="ping"),
    path("debug/", views.debug_status, name="debug_status"),  # <— TAMBAHKAN INI
    path("freight/quotation/add/", views.quotation_add_header, name="freight_quotation_add"),
    path("freight/quotation/add/<int:pk>/lines/", views.quotation_add_lines, name="freight_quotation_add_lines"),
    path("freight/quotation/list/", views.freight_quotation_list, name="freight_quotation_list"),
]
