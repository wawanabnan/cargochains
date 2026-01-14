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


from core.views.currencies import (
    CurrencyListView,
    CurrencyCreateView,
    CurrencyUpdateView,
    CurrencyDeleteView
)

from core.views.exchange_rates import (
    ExchangeRateListView, ExchangeRateCreateView, ExchangeRateUpdateView, ExchangeRateDeleteView
)

from core.views.taxes import TaxAutocompleteView

from core.views.settings_home import SettingsHomeView
from core.views.company import CompanyUpdateView


app_name = "core"

urlpatterns = [
    path("welcome/", welcome, name="welcome"),
    path("setup/user/", setup_user, name="setup_user"),
    path("setup/company/", setup_company, name="setup_company"),
    path("setup/done/", setup_done, name="setup_done"),    
    path("setup/general/", setup_general, name="setup_general"),
    
    path("sales/services/", ServiceListView.as_view(), name="service_list"),
    path("sales/add/", ServiceCreateView.as_view(), name="service_add"),
    path("sales/<int:pk>/", ServiceDetailView.as_view(), name="service_detail"),
    path("sales/<int:pk>/edit/", ServiceUpdateView.as_view(), name="service_edit"),
    path("sales/<int:pk>/delete/", ServiceDeleteView.as_view(), name="service_delete"),


    path("settings/taxes/", TaxListView.as_view(), name="tax_list"),
    path("settings/taxes/add/", TaxCreateView.as_view(), name="tax_add"),
    path("setting/taxes/<int:pk>/edit/", TaxUpdateView.as_view(), name="tax_edit"),
    path("taxes/<int:pk>/delete/", TaxDeleteView.as_view(), name="tax_delete"),
    path("taxes/autocomplete/", TaxAutocompleteView.as_view(), name="tax_autocomplete"),


    path("settings/tax-categories/", TaxCategoryListView.as_view(), name="tax_category_list"),
    path("settings/tax-categories/add/", TaxCategoryCreateView.as_view(), name="tax_category_add"),
    path("settings/tax-categories/<int:pk>/edit/", TaxCategoryUpdateView.as_view(), name="tax_category_edit"),
    path("tax-categories/<int:pk>/delete/", TaxCategoryDeleteView.as_view(), name="tax_category_delete"),


    path("settings/", SettingsHomeView.as_view(), name="settings_home"),
    path("settings/currencies/", CurrencyListView.as_view(), name="currency_list"),
    path("settings/currencies/add/", CurrencyCreateView.as_view(), name="currency_add"),
    path("settings/currencies/<int:pk>/edit/", CurrencyUpdateView.as_view(), name="currency_edit"),
    path("settings/currencies/<int:pk>/delete/", CurrencyDeleteView.as_view(), name="currency_delete"),

    path("settings/finance/exchange-rates/", ExchangeRateListView.as_view(), name="exchange_rate_list"),
    path("settings/finance/exchange-rates/add/", ExchangeRateCreateView.as_view(), name="exchange_rate_add"),
    path("settings/finance/exchange-rates/<int:pk>/edit/", ExchangeRateUpdateView.as_view(), name="exchange_rate_edit"),
    path("settings/finance/exchange-rates/<int:pk>/delete/", ExchangeRateDeleteView.as_view(), name="exchange_rate_delete"),

     path("settings/company/", CompanyUpdateView.as_view(), name="setup_company"),

]


from core.views.uoms import (
    UOMListView, UOMCreateView, UOMUpdateView, UOMDeleteView
)

from core.views.sales_config import SalesConfigView


urlpatterns += [
    path(
        "settings/products/uoms/",
        UOMListView.as_view(),
        name="uom_list"
    ),
    path(
        "settings/products/uoms/add/",
        UOMCreateView.as_view(),
        name="uom_add"
    ),
    path(
        "settings/products/uoms/<int:pk>/edit/",
        UOMUpdateView.as_view(),
        name="uom_edit"
    ),
    path(
        "settings/products/uoms/<int:pk>/delete/",
        UOMDeleteView.as_view(),
        name="uom_delete"
    ),
]



from core.views.number_sequences import (
    NumberSequenceListView, NumberSequenceCreateView,
    NumberSequenceUpdateView, NumberSequenceDeleteView
)

urlpatterns += [
    path("settings/system/numbering/", NumberSequenceListView.as_view(), name="numbering_list"),
    path("settings/system/numbering/add/", NumberSequenceCreateView.as_view(), name="numbering_add"),
    path("settings/system/numbering/<int:pk>/edit/", NumberSequenceUpdateView.as_view(), name="numbering_edit"),
    path("settings/system/numbering/<int:pk>/delete/", NumberSequenceDeleteView.as_view(), name="numbering_delete"),
    path("sales/config/",SalesConfigView.as_view(), name="sales_config"),
   
]




# core/urls_settings.py
from django.urls import path
from core.views.payment_terms import (
    PaymentTermListView,
    PaymentTermCreateView,
    PaymentTermUpdateView,
    PaymentTermDeleteView,
    PaymentTermSetDefaultView,
)


urlpatterns += [
    path("settings/payment-terms/", PaymentTermListView.as_view(), name="payment_term_list"),
    path("settings/payment-terms/add/", PaymentTermCreateView.as_view(), name="payment_term_add"),
    path("settings/payment-terms/<int:pk>/edit/", PaymentTermUpdateView.as_view(), name="payment_term_edit"),
    path("settings/payment-terms/<int:pk>/delete/", PaymentTermDeleteView.as_view(), name="payment_term_delete"),
    path("settings/payment-terms/<int:pk>/default/", PaymentTermSetDefaultView.as_view(), name="payment_term_set_default"),
]

from core.views.exchange_rates import (
    ExchangeRateLatestAPI,
    PullBIExchangeRateView,
    ExchangeRateActivateView

)

urlpatterns += [
    path("api/exchange-rate/latest/", ExchangeRateLatestAPI.as_view(), name="exchange_rate_latest_api"),
    path("api/exchange-rate/pull-bi/", PullBIExchangeRateView.as_view(), name="exchange_rate_pull_bi"),
    path("exchange-rates/<int:pk>/activate/", ExchangeRateActivateView.as_view(), name="exchange_rate_activate"),

]