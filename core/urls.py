from django.urls import path
from core.views.setup_company import setup_company
from core.views.welcome import welcome
from core.views.setup_admin import setup_user
from core.views.setup_done import setup_done


from core.views.setup_general import setup_general
from core.views.services import (
    ServiceListView,
    ServiceCreateView,
    ServiceUpdateView,
    ServiceDetailView,
    ServiceDeleteView,
)


from django.urls import path
from core.views.taxes import (
    TaxListView, TaxCreateView, TaxUpdateView, TaxDeleteView,
    TaxCategoryListView, TaxCategoryCreateView, TaxCategoryUpdateView, TaxCategoryDeleteView
)


app_name = "core"

urlpatterns = [
    path("welcome/", welcome, name="welcome"),
    path("setup/user/", setup_user, name="setup_user"),
    path("setup/company/", setup_company, name="setup_company"),
    path("setup/done/", setup_done, name="setup_done"),    
    path("setup/general/", setup_general, name="setup_general"),
    
    path("services/", ServiceListView.as_view(), name="service_list"),
    path("services/add/", ServiceCreateView.as_view(), name="service_add"),
    path("services/<int:pk>/", ServiceDetailView.as_view(), name="service_detail"),
    path("services/<int:pk>/edit/", ServiceUpdateView.as_view(), name="service_edit"),
    path("services/<int:pk>/delete/", ServiceDeleteView.as_view(), name="service_delete"),


    path("taxes/", TaxListView.as_view(), name="tax_list"),
    path("taxes/add/", TaxCreateView.as_view(), name="tax_add"),
    path("taxes/<int:pk>/edit/", TaxUpdateView.as_view(), name="tax_edit"),
    path("taxes/<int:pk>/delete/", TaxDeleteView.as_view(), name="tax_delete"),

    path("tax-categories/", TaxCategoryListView.as_view(), name="tax_category_list"),
    path("tax-categories/add/", TaxCategoryCreateView.as_view(), name="tax_category_add"),
    path("tax-categories/<int:pk>/edit/", TaxCategoryUpdateView.as_view(), name="tax_category_edit"),
    path("tax-categories/<int:pk>/delete/", TaxCategoryDeleteView.as_view(), name="tax_category_delete"),

]
