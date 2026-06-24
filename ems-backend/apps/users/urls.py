from django.urls import path

from .views import (
    LoginView,
    ChangePasswordView,
    EmailVerificationConfirmView,
    EmailVerificationRequestView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
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
    path(
        "email/verify/request/",
        EmailVerificationRequestView.as_view(),
        name="auth-email-verify-request",
    ),
    path(
        "email/verify/confirm/",
        EmailVerificationConfirmView.as_view(),
        name="auth-email-verify-confirm",
    ),
    path(
        "password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    path("phone/send-code/", SendPhoneCodeView.as_view(), name="auth-phone-send"),
    path("phone/verify-code/", VerifyPhoneCodeView.as_view(), name="auth-phone-verify"),
]
