from django.urls import path
from sales_configuration.views.dashboard import ConfigDashboardView
from sales_configuration.views.tax_config import SalesTaxConfigView
from .views.config_page import SalesConfigView


app_name = "sales_configuration"

urlpatterns = [
     path("tax/", SalesTaxConfigView.as_view(), name="tax_config"),
    path("", SalesConfigView.as_view(), name="config"),

]
