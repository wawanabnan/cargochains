from django.urls import path
from job.views.cost_types import CostTypeListView, CostTypeCreateView, CostTypeUpdateView
#from job.views.action import complete_job

from job.views.action import (
    job_confirm, job_hold, job_resume, job_complete, job_cancel
)


from job.views.job_order import (
   JobOrderListView,
   JobOrderCreateView,
   JobOrderUpdateView,
   JobOrderDetailView,
   JobOrderAttachmentUploadView,
   JobOrderAttachmentDeleteView,
   JobOrderBulkStatusView,
   JobOrderCostsUpdateView,
   JobOrderGenerateInvoiceView
    
)


app_name = "job"

urlpatterns = [
    path("cost-types/", CostTypeListView.as_view(), name="cost_type_list"),
    path("cost-types/add/", CostTypeCreateView.as_view(), name="cost_type_add"),
    path("cost-types/<int:pk>/edit/", CostTypeUpdateView.as_view(), name="cost_type_edit"),
   # path("order_completes/<int:pk>/complete/", complete_job, name="order_complete"),


    
    path("job-orders/", JobOrderListView.as_view(), name="job_order_list"),
    path("job-order/add/", JobOrderCreateView.as_view(), name="job_order_add"),
    path("job-order/<int:pk>/edit/", JobOrderUpdateView.as_view(), name="job_order_edit"),
    path("job-order/<int:pk>/", JobOrderDetailView.as_view(), name="job_order_detail"),
    #path("job-orders/<int:pk>/revenue-pdf/",JobOrderRevenuePdfView.as_view(),name="job_order_revenue_pdf"),
    path("job-orders/<int:pk>/attachments/add/",
         JobOrderAttachmentUploadView.as_view(),
         name="job_order_attachment_add"),
    path("job-orders/<int:pk>/attachments/<int:att_id>/delete/",
         JobOrderAttachmentDeleteView.as_view(),
         name="job_order_attachment_delete"),
    path(
        "job-orders/bulk-status/",
        JobOrderBulkStatusView.as_view(),
        name="joborder_bulk_status",
    ),
    path("job-orders/<int:pk>/costs/", JobOrderCostsUpdateView.as_view(), name="job_order_costs_update"),
    path(
        "job-orders/<int:pk>/generate-invoice/",
        JobOrderGenerateInvoiceView.as_view(),
        name="job_order_generate_invoice",
    ),

    path("job-orders/<int:pk>/confirm/", job_confirm, name="job_order_confirm"),
    path("job-orders/<int:pk>/resume/", job_resume, name="job_order_resume"),
    path("job-orders/<int:pk>/complete/", job_complete, name="job_order_complete"),
    path("job-orders/<int:pk>/cancel/", job_cancel, name="job_order_cancel"),


]

