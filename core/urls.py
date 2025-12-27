from django.urls import path
from core.views.company import company_settings
from core.views.setup_wizard import setup_step, setup_done
from core.views.company import company_settings  # halam
from core.views.welcome import welcome

from core.views.password_change import (
    password_change_required,
    InitialAdminPasswordChangeView,
    InitialAdminPasswordChangeDoneView,
)

app_name = "core"

urlpatterns = [
    path("settings/company/", company_settings, name="company_settings"),
    path("setup/<int:step>/", setup_step, name="setup_step"),
    path("setup/done/", setup_done, name="setup_done"),

    # settings normal (selalu bisa diakses setelah completed)
    path("settings/company/", company_settings, name="company_settings"),
    path("welcome/", welcome, name="welcome"),

    path("accounts/password/required/", password_change_required, name="password_change_required"),
    path("accounts/password/change/", InitialAdminPasswordChangeView.as_view(), name="password_change"),
    path("accounts/password/done/", InitialAdminPasswordChangeDoneView.as_view(), name="password_change_done"),

]

