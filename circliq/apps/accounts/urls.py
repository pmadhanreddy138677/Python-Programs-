from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("verify/resend/", views.ResendVerificationView.as_view(), name="resend_verification"),
    path("verify/<str:token>/", views.verify_email, name="verify_email"),
    path("password-reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("reset/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("settings/", views.account_settings, name="settings"),
    path("settings/deactivate/", views.deactivate_account, name="deactivate"),
    path("settings/delete/", views.delete_account, name="delete"),
    path("settings/export/", views.export_my_data, name="export"),
    path("reactivate/", views.reactivate_account, name="reactivate"),
]
