from django.urls import path
from work_orders.views.service_orders import (
    VendorBookingListView,
    VendorBookingCreateView,
    VendorBookingUpdateView,
    #VendorBookingJobCostRowsView,  # kalau ada endpoint ajax jobcosts
    VendorBookingFromJobCostWizardView,
    VendorBookingCreateJobCostsPartialView

)
from work_orders.views.print import VendorBookingPrintView
from work_orders.views.pdf import VendorBookingPdfView
from work_orders.views.actions import (
    VendorBookingSubmitView,
    VendorBookingApproveView,
    VendorBookingRejectView,
    VendorBookingConfirmView,
    VendorBookingSendView,
    VendorBookingCloseView,
    VendorBookingCancelView,
)

app_name = "work_orders"

urlpatterns = [
    # Service Orders (Vendor Booking)
    path("service-orders/", VendorBookingListView.as_view(), name="service_order_list"),
    path("service-orders/create/", VendorBookingCreateView.as_view(), name="service_order_create"),
    path("service-orders/<int:pk>/update/", VendorBookingUpdateView.as_view(), name="service_order_update"),

    # AJAX: jobcost rows (kalau dipakai di create)
    path("service-orders/create/jobcosts/",
         VendorBookingCreateJobCostsPartialView.as_view(), name="service_order_create_jobcosts"),

    # Print / PDF
    path("service-orders/<int:pk>/print/", VendorBookingPrintView.as_view(), name="service_order_print"),
    path("service-orders/<int:pk>/pdf/", VendorBookingPdfView.as_view(), name="service_order_pdf"),

    # Actions
    path("service-orders/<int:pk>/submit/", VendorBookingSubmitView.as_view(), name="service_order_submit"),
    
]

# work_orders/urls.py
from work_orders.views.attachment import (
    ServiceOrderAttachmentAddView,
    ServiceOrderAttachmentDeleteView,
)

urlpatterns += [
    path("service-orders/<int:pk>/attachments/add/", ServiceOrderAttachmentAddView.as_view(),
         name="service_order_attachment_add"),
    path("service-orders/<int:pk>/attachments/<int:att_id>/delete/", ServiceOrderAttachmentDeleteView.as_view(),
         name="service_order_attachment_delete"),
]


from work_orders.views.actions import (
    ServiceOrderSubmitView,
    ServiceOrderApproveView,
    ServiceOrderRejectView,
    ServiceOrderBackToDraftView,
    ServiceOrderMarkSentView,
    ServiceOrderConfirmVendorView,
    ServiceOrderCancelView,
    ServiceOrderMarkDoneView,
)

urlpatterns += [
    path("service-orders/<int:pk>/submit/", ServiceOrderSubmitView.as_view(), name="service_order_submit"),
    path("service-orders/<int:pk>/approve/", ServiceOrderApproveView.as_view(), name="service_order_approve"),
    path("service-orders/<int:pk>/reject/", ServiceOrderRejectView.as_view(), name="service_order_reject"),
    path("service-orders/<int:pk>/back-to-draft/", ServiceOrderBackToDraftView.as_view(), name="service_order_back_to_draft"),
    path("service-orders/<int:pk>/mark-sent/", ServiceOrderMarkSentView.as_view(), name="service_order_mark_sent"),
    path("service-orders/<int:pk>/confirm-vendor/", ServiceOrderConfirmVendorView.as_view(), name="service_order_confirm_vendor"),
    path("service-orders/<int:pk>/cancel/", ServiceOrderCancelView.as_view(), name="service_order_cancel"),
    path("service-orders/<int:pk>/done/", ServiceOrderMarkDoneView.as_view(), name="service_order_mark_done"),
]


#from work_orders.views.service_orders import ServiceOrderCreateJobcostsView

##urlpatterns += [
 #   path(
 #       "service-orders/create/jobcosts/",
 #       ServiceOrderCreateJobcostsView.as_view(),
 #       name="service_order_create_jobcosts",
 #   ),
#]