
from django.urls import path
from ..views.list import ShipmentListView
urlpatterns = [ path("", ShipmentListView.as_view(), name="list") ]
