from django.urls import path
from billing.views.customer_receipts import (
    CustomerReceiptListView, 
    CustomerReceiptCreateView, 
    CustomerReceiptDetailView, 
    CustomerReceiptPostView
)

from billing.views.api import invoice_customer_receipt_info

app_name = "billing"

urlpatterns = [
    path("receipts/", CustomerReceiptListView.as_view(), name="receipt_list"),
    path("receipts/add/", CustomerReceiptCreateView.as_view(), name="receipt_add"),
    path("receipts/<int:pk>/", CustomerReceiptDetailView.as_view(), name="receipt_detail"),
    path("receipts/<int:pk>/post/", CustomerReceiptPostView.as_view(), name="receipt_post"),
    path("api/invoice-receipt-info/", invoice_customer_receipt_info, name="api_invoice_receipt_info"),
]



# payments/urls.py
from django.urls import path

from billing.views.vendor_payments import (
   VendorPaymentListView,
    VendorPaymentCreateView,
    VendorPaymentUpdateView,
)


urlpatterns += [
    path("vendor-payments/", VendorPaymentListView.as_view(), name="vendor_payment_list"),
    path("vendor-payments/add/", VendorPaymentCreateView.as_view(), name="vendor_payment_add"),
    path("vendor-payments/<int:pk>/", VendorPaymentUpdateView.as_view(), name="vendor_payment_edit"),
]


from billing.views.invoices import (
    InvoiceListView, InvoiceUpdateView,
    InvoiceDetailView, InvoiceDeleteView, 
    InvoiceCreateManualView,
    InvoiceConfirmView
)

from .views.invoice_pdf_html import InvoicePdfHtmlView  # sesuaikan path
from .views.invoice_preview import InvoicePreviewView

urlpatterns += [

    path("billing/invoices/", InvoiceListView.as_view(), name="invoice_list"),
    path("billing/invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path("billing/<int:pk>/edit/", InvoiceUpdateView.as_view(), name="invoice_edit"),
    path("billing/<int:pk>/delete/", InvoiceDeleteView.as_view(), name="invoice_delete"),

    # optional: generate invoice from job order via modal/form
    path("billing/add/", InvoiceCreateManualView.as_view(), name="invoice_add"),
    # sales/urls.py
   
   
     path(
        "billing/invoices/<int:pk>/pdf/",
         InvoicePdfHtmlView.as_view(),
         name="invoice_pdf",
    ),
    path(
        "invoice/<int:pk>/preview/",
        InvoicePreviewView.as_view(),
        name="invoice_preview",
    ),

     path("billing/invoices/<int:pk>/confirm/", InvoiceConfirmView.as_view(), name="invoice_confirm"),

]

from billing.views.config import BillingConfigUpdateView
urlpatterns += [

    path("billing/config/", BillingConfigUpdateView.as_view(), name="config"),

]
