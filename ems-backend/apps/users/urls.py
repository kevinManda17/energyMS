from django.urls import path

from .views import (
    LoginView,
    ChangePasswordView,
    MeView,
    RefreshView,
    RegisterView,
    SendPhoneCodeView,
    VerifyPhoneCodeView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    path("phone/send-code/", SendPhoneCodeView.as_view(), name="auth-phone-send"),
    path("phone/verify-code/", VerifyPhoneCodeView.as_view(), name="auth-phone-verify"),
]
