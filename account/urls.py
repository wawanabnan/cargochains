# account/urls.py
from django.urls import path
from .views import UserLoginView, DashboardView, LenientLogoutView

app_name = "account"
urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("logout/", LenientLogoutView.as_view(), name="logout"),
]
