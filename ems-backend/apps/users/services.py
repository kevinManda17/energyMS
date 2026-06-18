import logging
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from .models import PhoneVerificationCode

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
