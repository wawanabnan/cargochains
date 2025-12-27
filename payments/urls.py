from django.urls import path
from payments.views.receipts import (
    ReceiptListView, ReceiptCreateView, ReceiptDetailView, ReceiptPostView
)

from payments.views.api import invoice_receipt_info

app_name = "payments"

urlpatterns = [
    path("receipts/", ReceiptListView.as_view(), name="receipt_list"),
    path("receipts/add/", ReceiptCreateView.as_view(), name="receipt_add"),
    path("receipts/<int:pk>/", ReceiptDetailView.as_view(), name="receipt_detail"),
    path("receipts/<int:pk>/post/", ReceiptPostView.as_view(), name="receipt_post"),
    path("api/invoice-receipt-info/", invoice_receipt_info, name="api_invoice_receipt_info"),
]

