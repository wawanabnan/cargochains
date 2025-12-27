from django.contrib import admin
from accounting.models.chart import Account
from accounting.models.journal import Journal, JournalLine
from accounting.models.period_lock import AccountingPeriodLock
from accounting.models.settings import  AccountingSettings


@admin.register(AccountingPeriodLock)
class AccountingPeriodLockAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "is_locked", "locked_at")
    list_filter = ("year", "is_locked")
    ordering = ("-year", "-month")

@admin.register(AccountingSettings)
class AccountingSettingsAdmin(admin.ModelAdmin):
    list_display = ("active_fiscal_year",)