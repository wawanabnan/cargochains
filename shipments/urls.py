from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required


from . import views
#from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine
from shipments.api.public.views import PublicTrackShipmentView
from shipments.views.ops import TripDispatchPickupView, TripDepartView, TripArriveView
from shipments.views.ops import ShipmentPODUploadView
from django.views.decorators.csrf import csrf_exempt
from django.urls import path
from .api.internal.pod import ShipmentPodUploadView 
from shipments.views.ops_public_link import ShipmentPublicLinkView
from rest_framework.authtoken.views import obtain_auth_token
from shipments.views.cs_portal import cs_public_link_page

from shipments.views.internal_cs import shipment_public_link_page
from shipments.views.public_page import public_tracking_page, public_tracking_page,  public_track_home 


app_name = "shipments"

urlpatterns = [
   # SYSTEM (API)
#path("api/public/track/<str:tracking_no>/", PublicTrackShipmentView.as_view(), name="public-track"),
path("api/ops/trips/<int:trip_id>/dispatch/", csrf_exempt(TripDispatchPickupView.as_view()), name="ops-trip-dispatch"),
path("api/token/", obtain_auth_token),  # optional
path("api/ops/shipments/<str:tracking_no>/pod/", ShipmentPodUploadView.as_view(), name="ops-shipment-pod"),

# INTERNAL (CS/Ops)
path("internal/cs/public-link/",  cs_public_link_page, name="cs_public_link_page"),

# CUSTOMER (Public Web)
path("track/", public_track_home, name="public_track_home"),
path("track/<str:tracking_no>/", public_tracking_page, name="public_tracking_page"),


]


app_name = "shipments"


from shipments.views.vendor_bills import VendorBillListView, VendorBillCreateView, VendorBillUpdateView

urlpatterns += [
    path("vendor-bills/", VendorBillListView.as_view(), name="vendor_bill_list"),
    path("vendor-bills/add/", VendorBillCreateView.as_view(), name="vendor_bill_add"),
    path("vendor-bills/<int:pk>/", VendorBillUpdateView.as_view(), name="vendor_bill_edit"),
]



from django.urls import path




from shipments.views.vendor_bills import VendorBillListView, VendorBillCreateView, VendorBillUpdateView

urlpatterns += [
    path("vendor-bills/", VendorBillListView.as_view(), name="vendor_bill_list"),
    path("vendor-bills/add/", VendorBillCreateView.as_view(), name="vendor_bill_add"),
    path("vendor-bills/<int:pk>/", VendorBillUpdateView.as_view(), name="vendor_bill_edit"),
]


from django.urls import path
from shipments.views.shipping_instruction import (
    ShippingInstructionListView,
    ShippingInstructionDetailView,
    ShippingInstructionUpdateView,
    ShippingInstructionIssueView,
    ShippingInstructionCancelView
)

urlpatterns += [
    path("shipping-instructions/", ShippingInstructionListView.as_view(), name="si_list"),
    path("shipping-instructions/<int:pk>/", ShippingInstructionDetailView.as_view(), name="si_detail"),
    path("shipping-instructions/<int:pk>/edit/", ShippingInstructionUpdateView.as_view(), name="si_update"),
    path("shipping-instructions/<int:pk>/issue/",ShippingInstructionIssueView.as_view(),name="si_issue"),
    path("shipping-instructions/<int:pk>/cancel/",ShippingInstructionCancelView.as_view(),name="si_cancel"),
]



from django.urls import path
from shipments.views.public_tracking import PublicTrackAPIView

urlpatterns += [
    path("api/public/track/<str:tracking_no>/", PublicTrackAPIView.as_view(), name="public-track"),
]
