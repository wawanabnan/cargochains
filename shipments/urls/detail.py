
from django.urls import path
from ..views.detail import ShipmentDetailView
urlpatterns = [ path("<int:pk>/view/", ShipmentDetailView.as_view(), name="view") ]
