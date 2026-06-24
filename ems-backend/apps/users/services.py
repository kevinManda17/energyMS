import logging
import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailVerificationToken, PasswordResetToken, PhoneVerificationCode

logger = logging.getLogger(__name__)


class SMSProvider:
    """Minimal SMS provider abstraction for future production providers."""

    def send_code(self, phone: str, code: str) -> None:
        provider = getattr(settings, "SMS_PROVIDER", "console")
        if provider != "console":
            logger.info("SMS provider %s is not configured yet; using console fallback.", provider)
        logger.info("EMS phone verification code for %s: %s", phone, code)


def create_phone_verification(phone: str) -> tuple[PhoneVerificationCode, str]:
    code = f"{random.randint(100000, 999999)}"
    verification = PhoneVerificationCode.objects.create(
        phone=phone,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    SMSProvider().send_code(phone, code)
    return verification, code


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def create_email_verification(user) -> tuple[EmailVerificationToken, str]:
    token = _new_token()
    verification = EmailVerificationToken.objects.create(
        user=user,
        token_hash=make_password(token),
        expires_at=timezone.now()
        + timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_MINUTES),
    )
    url = f"{settings.FRONTEND_URL}/verify-email?email={user.email}&token={token}"
    send_mail(
        "Verification de votre adresse e-mail EMS",
        f"Bonjour {user.username},\n\nConfirmez votre adresse e-mail : {url}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )
    return verification, token


def create_password_reset(user) -> tuple[PasswordResetToken, str]:
    token = _new_token()
    reset = PasswordResetToken.objects.create(
        user=user,
        token_hash=make_password(token),
        expires_at=timezone.now() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_MINUTES),
    )
    url = f"{settings.FRONTEND_URL}/reset-password?email={user.email}&token={token}"
    send_mail(
        "Reinitialisation de votre mot de passe EMS",
        f"Bonjour {user.username},\n\nReinitialisez votre mot de passe : {url}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )
    return reset, token
