# sales/urls.py
from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required

# CBV: Lists & Details
from .views.lists import FreightQuotationListView, FreightOrderListView
from .views.details import FreightQuotationDetailView, FreightOrderDetailView

# FBV: Add / Edit / Print / PDF / Actions
#from .views.adds import quotation_add_header, quotation_add_lines
from .views.adds import FreightQuotationAddView  # ⬅️ ganti ini
from .views.edits import FreightQuotationEditView 
from .views.prints import quotation_print, quotation_pdf, order_print, order_pdf



from .auth import sales_access_required
from .views import actions as action_views
from .views import freight  # pastikan __init__.py di views sudah import freight, atau pakai from .views.freight import ...



from .views.freight import (
    FqListView,
    FqCreateView,
    FqUpdateView,
    FqDetailView,
    FqDeleteView,
    FqBulkDeleteView,
    FqStatusUpdateView,
    FoListView,
    FoDetailView,
    FoStatusUpdateView,
    FoEditFieldsView
)

from sales.views.invoices import (
    InvoiceListView, InvoiceUpdateView,
    InvoiceDetailView, InvoiceDeleteView, 
    InvoiceCreateManualView,
    InvoiceConfirmView
)

from .views.freight_pdf import  FreightQuotationPdfHtmlView
from .views.fo_pdf import FreightOrderPdfHtmlView  # sesuaikan path
from .views.invoice_pdf_html import InvoicePdfHtmlView  # sesuaikan path


from .views.job_order import (
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

from .views.jo_revenue_pdf import JobOrderRevenuePdfView

from .views.customers import (
    CustomerListView, CustomerCreateView, CustomerDetailView,
    CustomerUpdateView, CustomerDeleteView,
     CustomerContactCreateView,
     CustomerContactUpdateView
)


app_name = "sales"

urlpatterns = [
    # ===== QUOTATIONS =====
    path("freight/quotations/",                   FreightQuotationListView.as_view(),   name="quotation_list"),
    path("freight/quotations/<int:pk>/",          FreightQuotationDetailView.as_view(), name="quotation_details"),  # ← pakai nama plural 'details'
 
    path("freight/quotations/add/",               FreightQuotationAddView.as_view(),  name="quotation_add"),
    path("freight/quotations/<int:pk>/edit/",     FreightQuotationEditView.as_view(),  name="quotation_edit"),


   # path("freight/quotations/lines/",                login_required(quotation_add_lines,  login_url="account:login"), name="quotation_add_lines"),
   
    path("freight/quotations/<int:pk>/print/",       login_required(quotation_print,      login_url="account:login"), name="quotation_print"),
    path("freight/quotations/<int:pk>/pdf/",         login_required(quotation_pdf,        login_url="account:login"), name="quotation_pdf"),

    # ===== ORDERS =====
    path("freight/orders/",                          FreightOrderListView.as_view(),       name="order_list"),
    path("freight/orders/<int:pk>/",                 FreightOrderDetailView.as_view(),     name="order_details"),     # ← pakai nama plural 'details'

    # ===== LEGACY ALIASES (biar reverse lama '..._detail' tetap hidup) =====
    path("freight/quotations/<int:pk>/",             FreightQuotationDetailView.as_view(), name="quotation_detail"),
    path("freight/orders/<int:pk>/",                 FreightOrderDetailView.as_view(),     name="order_detail"),

    # ===== LEGACY REDIRECTS (singular → plural) =====
    path("freight/quotation/",                       RedirectView.as_view(pattern_name="sales:quotation_list",  permanent=False)),
    path("freight/quotation/<int:pk>/",              RedirectView.as_view(pattern_name="sales:quotation_details", permanent=False)),
    path("freight/order/",                           RedirectView.as_view(pattern_name="sales:order_list",       permanent=False)),
    path("freight/order/<int:pk>/",                  RedirectView.as_view(pattern_name="sales:order_details",     permanent=False)),
    path("freight/quotation/add/",                   RedirectView.as_view(pattern_name="sales:quotation_add",     permanent=False)),
    path("freight/quotation/lines/",                 RedirectView.as_view(pattern_name="sales:quotation_add_lines", permanent=False)),

    #path("freight/quotations/<int:pk>/generate-so/", sales_access_required(quotation_generate_so), name="quotation_generate_so"),
    #path("freight/orders/<int:pk>/status/", action_views.order_set_status, name="order_set_status"),

    # sales/urls.py
    path("quotations/", FqListView.as_view(), name="fq_list"),
    path("quotations/add/", FqCreateView.as_view(), name="fq_add"),
    path("quotations/<int:pk>/edit/", FqUpdateView.as_view(), name="fq_edit"),
    
    path(
        "quotations/<int:pk>/",
        FqDetailView.as_view(),
        name="fq_detail",
    ),
     path(
        "quotations/<int:pk>/delete/",
        FqDeleteView.as_view(),
        name="fq_delete",
    ),

    # Bulk delete
    path(
        "quotations/bulk-delete/",
        FqBulkDeleteView.as_view(),
        name="fq_bulk_delete",
    ),
   
    path(
        "quotations/<int:pk>/pdf/",
        FreightQuotationPdfHtmlView.as_view(),
        name="fq_pdf",
    ),

    path(
        "quotations/<int:pk>/status/",
        FqStatusUpdateView.as_view(),
        name="fq_change_status",
    ),

    # FREIGHT ORDERS
    path("freight-orders/", FoListView.as_view(), name="fo_list"),
    path("freight-orders/<int:pk>/", FoDetailView.as_view(), name="fo_detail"),
    path("freight-orders/<int:pk>/status/", FoStatusUpdateView.as_view(), name="fo_change_status"),
    path("freight-orders/<int:pk>/edit-fields/", FoEditFieldsView.as_view(), name="fo_edit_fields"),
    path(
        "freight-orders/<int:pk>/print/",
        FreightOrderPdfHtmlView.as_view(),
        name="fo_pdf",
    ),
    
    #path("job-orders/", JobOrderListView.as_view(), name="job_order_list"),
    #path("job-order/add/", JobOrderCreateView.as_view(), name="job_order_add"),
    #path("job-order/<int:pk>/edit/", JobOrderUpdateView.as_view(), name="job_order_edit"),
    #path("job-order/<int:pk>/", JobOrderDetailView.as_view(), name="job_order_detail"),
    #path("job-orders/<int:pk>/revenue-pdf/",JobOrderRevenuePdfView.as_view(),name="job_order_revenue_pdf"),
    #path("job-orders/<int:pk>/attachments/add/",
    #     JobOrderAttachmentUploadView.as_view(),
    #     name="job_order_attachment_add"),
    #path("job-orders/<int:pk>/attachments/<int:att_id>/delete/",
    #     JobOrderAttachmentDeleteView.as_view(),
    #     name="job_order_attachment_delete"),
    #path(
    #    "job-orders/bulk-status/",
    #    JobOrderBulkStatusView.as_view(),
    #    name="joborder_bulk_status",
    #),
    #path("job-orders/<int:pk>/costs/", JobOrderCostsUpdateView.as_view(), name="job_order_costs_update"),
    #path(
    #    "job-orders/<int:pk>/generate-invoice/",
    #    JobOrderGenerateInvoiceView.as_view(),
    #    name="job_order_generate_invoice",
    #),


    path("customers/", CustomerListView.as_view(), name="customer_list"),
    path("customers/add/", CustomerCreateView.as_view(), name="customer_add"),
    path("customers/<int:pk>/", CustomerDetailView.as_view(), name="customer_detail"),
    path("customers/<int:pk>/edit/", CustomerUpdateView.as_view(), name="customer_edit"),
    path("customers/<int:pk>/delete/", CustomerDeleteView.as_view(), name="customer_delete"),
    path("customers/<int:pk>/contacts/add/", CustomerContactCreateView.as_view(), name="customer_contact_add"),
    path("customers/contacts/<int:pk>/update/", CustomerContactUpdateView.as_view(), name="customer_contact_update"),


    path("invoices/", InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/edit/", InvoiceUpdateView.as_view(), name="invoice_edit"),
    path("invoices/<int:pk>/delete/", InvoiceDeleteView.as_view(), name="invoice_delete"),

    # optional: generate invoice from job order via modal/form
    path("invoices/add/", InvoiceCreateManualView.as_view(), name="invoice_add"),
    # sales/urls.py
   
   
     path(
        "invoices/<int:pk>/pdf/",
         InvoicePdfHtmlView.as_view(),
         name="invoice_pdf",
    ),

     path("invoices/<int:pk>/confirm/", InvoiceConfirmView.as_view(), name="invoice_confirm"),



]




from sales.views.vendors import (
    VendorListView, VendorCreateView, VendorUpdateView, VendorDetailView, VendorDeleteView,
    VendorContactCreateView, VendorContactUpdateView,
)

urlpatterns += [
    path("vendors/", VendorListView.as_view(), name="vendor_list"),
    path("vendors/add/", VendorCreateView.as_view(), name="vendor_add"),
    path("vendors/<int:pk>/", VendorDetailView.as_view(), name="vendor_detail"),
    path("vendors/<int:pk>/edit/", VendorUpdateView.as_view(), name="vendor_edit"),
    path("vendors/<int:pk>/delete/", VendorDeleteView.as_view(), name="vendor_delete"),

    path("vendors/<int:pk>/contacts/add/", VendorContactCreateView.as_view(), name="vendor_contact_add"),
    path("vendors/contacts/<int:pk>/update/", VendorContactUpdateView.as_view(), name="vendor_contact_update"),
]




