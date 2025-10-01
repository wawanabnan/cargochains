
from django.urls import path
from . import views

app_name = "shipments"

urlpatterns = [
    path("", views.shipment_list, name="list"),
    path("new/", views.shipment_create, name="create"),
    path("<int:pk>/", views.shipment_edit, name="edit"),
    path("<int:pk>/add-log/", views.add_status_log, name="add_log"),
]
