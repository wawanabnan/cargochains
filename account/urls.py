from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("users/", views.users_list, name="users_list"),
]
