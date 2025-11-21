from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required

from .views.details import ShipmentDetailView
from .views.lists import ShipmentListView
from .views.actions import shipment_confirm, shipment_book, shipment_attach, shipment_detach,shipment_update_parties
from .views.manual_routes import edit_routes
from .views.routes_inline import route_modal, route_delete
from .views.routes_schedule import routes_schedule, routes_schedule_export
from .views import routes_api
from shipments.views.routes_inline import route_modal, route_delete, route_delete_confirm

from .views.create import ShipmentCreateView

app_name = "shipments"

urlpatterns = [
    path("<int:pk>/", ShipmentDetailView.as_view(), name="shipment_details"),
    path("", ShipmentListView.as_view(), name="shipment_list"),
    path("<int:pk>/confirm/", shipment_confirm, name="shipment_confirm"),
    path("<int:pk>/book/", shipment_book, name="shipment_book"),
    path("<int:pk>/attach/", shipment_attach, name="shipment_attach"),
    path("<int:pk>/attachments/<int:att_pk>/delete/", shipment_detach, name="shipment_detach"),

    # ⬇️ Halaman form Parties & Cargo
    path("shipments/<int:pk>/edit-parties/", shipment_update_parties, name="shipment_update_parties"),
    path("<int:shipment_id>/routes/", edit_routes, name="shipment_routes_edit"),


    path("<int:shipment_id>/routes/modal/", route_modal, name="shipment_route_add_modal"),
    path("<int:shipment_id>/routes/<int:route_id>/modal/", route_modal, name="shipment_route_edit_modal"),


    path("<int:shipment_id>/routes/<int:route_id>/delete/confirm/", route_delete_confirm, name="shipment_route_delete_confirm"),
    path("<int:shipment_id>/routes/<int:route_id>/delete/", route_delete, name="shipment_route_delete"),


    path("routes/schedule/", routes_schedule, name="routes_schedule"),
    path("routes/schedule/export/", routes_schedule_export, name="routes_schedule_export"),  # opsional CSV

    path("api/assets/by-type/<int:type_id>/", routes_api.assets_by_type, name="assets_by_type"),

    path("create/", ShipmentCreateView.as_view(), name="create"),


]
