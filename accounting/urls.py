from django.urls import path

from accounting.views.journals import JournalListView, JournalDetailView, JournalPostView
from accounting.views.journals_manual import JournalCreateView, JournalUpdateView
from accounting.views.accounts import account_autocomplete
from accounting.views.account_charts import (
    AccountListView, AccountCreateView, AccountImportView,
    AccountExportCsvView,AccountTreeView,
    AccountDetailView, AccountUpdateView    
)

from accounting.views.reports import TrialBalanceView
from accounting.views.reports import GeneralLedgerView
from accounting.views.period_locks import (
    PeriodLockListView, PeriodLockCreateView, PeriodLockUpdateView, PeriodLockToggleView
)

from accounting.views.settings import AccountingSettingsUpdateView
from accounting.views.configuration import AccountingConfigurationView


app_name = "accounting"

urlpatterns = [
    path("journals/", JournalListView.as_view(), name="journal_list"),
    path("journals/add/", JournalCreateView.as_view(), name="journal_add"),
    path("journals/<int:pk>/edit/", JournalUpdateView.as_view(), name="journal_edit"),
    path("journals/<int:pk>/", JournalDetailView.as_view(), name="journal_detail"),
    path("journals/<int:pk>/post/", JournalPostView.as_view(), name="journal_post"),
    path("accounts/autocomplete/", account_autocomplete, name="account_autocomplete"),
    path("accounts/", AccountListView.as_view(), name="account_list"),
    path("accounts/add/", AccountCreateView.as_view(), name="account_add"),
    path("accounts/import/", AccountImportView.as_view(), name="account_import"),
    path("accounts/export/", AccountExportCsvView.as_view(), name="account_export"),
    path("accounts/tree/", AccountTreeView.as_view(), name="account_tree"),
    path("accounts/<int:pk>/", AccountDetailView.as_view(), name="account_detail"),
    path("accounts/<int:pk>/edit/", AccountUpdateView.as_view(), name="account_edit"),
    path("reports/trial-balance/", TrialBalanceView.as_view(), name="trial_balance"),
    path("reports/general-ledger/<int:account_id>/", GeneralLedgerView.as_view(), name="general_ledger"),

    
    path("settings/period-locks/", PeriodLockListView.as_view(), name="period_lock_list"),
    path("settings/period-locks/add/", PeriodLockCreateView.as_view(), name="period_lock_add"),
    path("settings/period-locks/<int:pk>/edit/", PeriodLockUpdateView.as_view(), name="period_lock_edit"),
    path("settings/period-locks/<int:pk>/toggle/", PeriodLockToggleView.as_view(), name="period_lock_toggle"),
    path("settings/", AccountingSettingsUpdateView.as_view(), name="settings"),
    path("configuration/", AccountingConfigurationView.as_view(), name="configuration"),

    
]

