from django.urls import path
from job.views.job_cost_types import CostTypeListView, CostTypeCreateView, CostTypeUpdateView
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
   JobOrderGenerateInvoiceView,
  
    
)

from job.views.job_cost_types import (
     cost_type_export,
   cost_type_import
)

from django.urls import path, include

from job.views.reports import sales_report, sales_report_pdf


app_name = "job"

urlpatterns = [
    path("cost-types/", CostTypeListView.as_view(), name="cost_type_list"),
    path("cost-types/add/", CostTypeCreateView.as_view(), name="cost_type_add"),
    path("cost-types/<int:pk>/edit/", CostTypeUpdateView.as_view(), name="cost_type_edit"),
   # path("order_completes/<int:pk>/complete/", complete_job, name="order_complete"),

    path("cost-types/export/", cost_type_export, name="cost_type_export"),
    path("cost-types/import/", cost_type_import, name="cost_type_import"),


    
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


    path("job-order/<int:pk>/confirm/", job_confirm, name="job_confirm"),
    path("job-order/<int:pk>/hold/", job_hold, name="job_hold"),
    path("job-order/<int:pk>/resume/", job_resume, name="job_resume"),
    path("job-order/<int:pk>/complete/", job_complete, name="job_complete"),
    path("job-order/<int:pk>/cancel/", job_cancel, name="job_cancel"),
       
    path("reports/job/", sales_report, name="sales_report"),
    path("reports/job/pdf/", sales_report_pdf, name="sales_report_pdf"),
         


]


# job/urls.py
from django.urls import path
from job.views.job_order_cost_print import joborder_cost_print_preview
from job.views.job_order_cost_pdf import joborder_cost_pdf_wkhtml
from job.views.job_order_cost_plypdf import joborder_cost_pdf
from job.views.job_order_pdf import test_weasyprint

urlpatterns += [
    path("job-orders/<int:pk>/costs/print/", joborder_cost_print_preview, name="joborder_cost_print_preview"),
    #path("job-orders/<int:pk>/costs/print.pdf", joborder_cost_pdf, name="joborder_cost_pdf"),
    path("job-orders/<int:pk>/costs/print.pdf", joborder_cost_pdf, name="joborder_cost_pdf"),
    path("job-orders/<int:pk>/costs/print.pdf", joborder_cost_pdf_wkhtml, name="joborder_cost_pdf_2"),
    path("test-weasyprint/", test_weasyprint, name="test_weasyprint"),
   
]


from django.urls import path
from job.views.quotations import (
    QuotationListView, QuotationCreateView, QuotationUpdateView,
    QuotationStatusUpdateView,QuotationSendView,QuotationDetailView,
     QuotationConvertToOrderView,QuotationPrintPreviewView,
    QuotationPDFView,
)

urlpatterns += [
    path("quotations/", QuotationListView.as_view(), name="quotation_list"),
    path("quotations/add/", QuotationCreateView.as_view(), name="quotation_add"),
    path("quotations/<int:pk>/", QuotationDetailView.as_view(), name="quotation_detail"),
    path("quotations/<int:pk>/edit/", QuotationUpdateView.as_view(), name="quotation_update"),
    path("quotations/<int:pk>/status/", QuotationStatusUpdateView.as_view(), name="quotation_update_status"),
    path("quotations/<int:pk>/send/", QuotationSendView.as_view(), name="quotation_send"),
    path("quotations/<int:pk>/convert/", QuotationConvertToOrderView.as_view(), name="quotation_convert"),
    path("quotations/<int:pk>/print/", QuotationPrintPreviewView.as_view(), name="quotation_print"),
    path("quotations/<int:pk>/pdf/", QuotationPDFView.as_view(), name="quotation_pdf"),

]
    

# job/urls.py
from job.views.job_order_print import JobOrderPrintPreviewView, JobOrderPDFView

urlpatterns += [
    path("job-orders/<int:pk>/print-preview/", JobOrderPrintPreviewView.as_view(), name="job_order_print_preview"),
    path("job-orders/<int:pk>/print/", JobOrderPDFView.as_view(), name="job_order_pdf"),
]
