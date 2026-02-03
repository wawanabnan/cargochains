from django.urls import path
from shipments.views.cs_portal import (
    cs_login_view,
    cs_logout_view,
    cs_home_view,
    cs_shipment_view,
)

urlpatterns = [
    path("cs/login/", cs_login_view, name="cs_login"),
    path("cs/logout/", cs_logout_view, name="cs_logout"),

    path("cs/", cs_home_view, name="cs_home"),
    path("cs/shipments/<int:shipment_id>/", cs_shipment_view, name="cs_shipment"),
]
