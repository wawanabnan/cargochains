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
path("api/public/track/<str:tracking_no>/", PublicTrackShipmentView.as_view(), name="public-track"),
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



from shipments.views.vendor_booking_print import VendorBookingPrintView, VendorBookingPdfView
from shipments.views.vendor_booking_confirm import VendorBookingConfirmView

from shipments.views.vendor_bookings import (
   
    VendorBookingFromJobCostWizardView,
    VendorBookingListView,
    VendorBookingUpdateView,
    
)




urlpatterns += [
    # STEP 2 Wizard
    path("vendor-bookings/from-jobcost/",VendorBookingFromJobCostWizardView.as_view(),name="vendor_booking_from_jobcost",),
    path("vendor-bookings/<int:pk>/print/",VendorBookingPrintView.as_view(),name="vendor_booking_print",),
    path("vendor-bookings/<int:pk>/pdf/", VendorBookingPdfView.as_view(), name="vendor_booking_pdf"),
    path("vendor-bookings/<int:pk>/confirm/", VendorBookingConfirmView.as_view(), name="vendor_booking_confirm"),
    path("vendor-bookings/", VendorBookingListView.as_view(), name="vendor_booking_list"),
    path("vendor-bookings/<int:pk>/update/",  VendorBookingUpdateView.as_view(),  name="vendor_booking_update",)
   

 
]




from shipments.views.vendor_booking_actions import (
    VendorBookingSubmitView,
    VendorBookingApproveView,
    VendorBookingRejectView,
    VendorBookingConfirmView,
    VendorBookingSendView,
    VendorBookingCloseView,
    VendorBookingCancelView,
)

urlpatterns += [
    path("vendor-bookings/<int:pk>/submit/", VendorBookingSubmitView.as_view(), name="vendor_booking_submit"),
    path("vendor-bookings/<int:pk>/approve/", VendorBookingApproveView.as_view(), name="vendor_booking_approve"),
    path("vendor-bookings/<int:pk>/reject/", VendorBookingRejectView.as_view(), name="vendor_booking_reject"),
    path("vendor-bookings/<int:pk>/confirm/", VendorBookingConfirmView.as_view(), name="vendor_booking_confirm"),
    path("vendor-bookings/<int:pk>/send/", VendorBookingSendView.as_view(), name="vendor_booking_send"),
    path("vendor-bookings/<int:pk>/close/", VendorBookingCloseView.as_view(), name="vendor_booking_close"),
    path("vendor-bookings/<int:pk>/cancel/", VendorBookingCancelView.as_view(), name="vendor_booking_cancel"),

]



from shipments.views.vendor_bills import VendorBillListView, VendorBillCreateView, VendorBillUpdateView

urlpatterns += [
    path("vendor-bills/", VendorBillListView.as_view(), name="vendor_bill_list"),
    path("vendor-bills/add/", VendorBillCreateView.as_view(), name="vendor_bill_add"),
    path("vendor-bills/<int:pk>/", VendorBillUpdateView.as_view(), name="vendor_bill_edit"),
]













