from django.urls import path
from payments.views.customer_receipts import (
    CustomerReceiptListView, 
    CustomerReceiptCreateView, 
    CustomerReceiptDetailView, 
    CustomerReceiptPostView
)

from payments.views.api import invoice_customer_receipt_info

app_name = "payments"

urlpatterns = [
    path("receipts/", CustomerReceiptListView.as_view(), name="receipt_list"),
    path("receipts/add/", CustomerReceiptCreateView.as_view(), name="receipt_add"),
    path("receipts/<int:pk>/", CustomerReceiptDetailView.as_view(), name="receipt_detail"),
    path("receipts/<int:pk>/post/", CustomerReceiptPostView.as_view(), name="receipt_post"),
    path("api/invoice-receipt-info/", invoice_customer_receipt_info, name="api_invoice_receipt_info"),
]



# payments/urls.py
from django.urls import path

from payments.views.vendor_payments import (
   VendorPaymentListView,
    VendorPaymentCreateView,
    VendorPaymentUpdateView,
)


app_name = "payments"

urlpatterns += [
    path("vendor-payments/", VendorPaymentListView.as_view(), name="vendor_payment_list"),
    path("vendor-payments/add/", VendorPaymentCreateView.as_view(), name="vendor_payment_add"),
    path("vendor-payments/<int:pk>/", VendorPaymentUpdateView.as_view(), name="vendor_payment_edit"),
]
