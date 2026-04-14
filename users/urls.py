from django.urls import path
from .views import register, user_login, user_logout, user_profile, password_reset_request_view, password_reset_code_view, password_reset_new_view, password_reset_resend_view

app_name = "users"

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("profile/", user_profile, name="profile"),
    path("password-reset/", password_reset_request_view, name="password_reset_request"),
    path("password-reset/code/", password_reset_code_view, name="password_reset_code"),
    path("password-reset/new/", password_reset_new_view, name="password_reset_new"),
    path("password-reset/resend/", password_reset_resend_view, name="password_reset_resend"),
]