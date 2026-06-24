from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    ChangePasswordSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SendPhoneCodeSerializer,
    UserSerializer,
    VerifyPhoneCodeSerializer,
)
from .services import create_email_verification, create_password_reset, create_phone_verification


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — public account creation."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ — current user profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class SendPhoneCodeView(APIView):
    """POST /api/auth/phone/send-code/."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SendPhoneCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification, code = create_phone_verification(
            serializer.validated_data["phone"]
        )
        payload = {
            "detail": "Code de verification envoye.",
            "expires_at": verification.expires_at,
        }
        if settings.DEBUG:
            payload["dev_code"] = code
        return Response(payload, status=status.HTTP_201_CREATED)


class VerifyPhoneCodeView(APIView):
    """POST /api/auth/phone/verify-code/."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyPhoneCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = serializer.validated_data["verification"]
        return Response(
            {
                "verified": True,
                "phone": verification.phone,
                "phone_verification_token": verification.id,
            }
        )


class ChangePasswordView(APIView):
    """POST /api/auth/password/change/."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Mot de passe modifie."})


class EmailVerificationRequestView(APIView):
    """POST /api/auth/email/verify/request/."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailVerificationRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        payload = {"detail": "Si le compte existe, un e-mail de verification est envoye."}
        if user:
            verification, token = create_email_verification(user)
            payload["expires_at"] = verification.expires_at
            if settings.DEBUG:
                payload["dev_token"] = token
        return Response(payload, status=status.HTTP_201_CREATED)


class EmailVerificationConfirmView(APIView):
    """POST /api/auth/email/verify/confirm/."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"verified": True, "email": user.email})


class PasswordResetRequestView(APIView):
    """POST /api/auth/password/reset/request/."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        payload = {"detail": "Si le compte existe, un e-mail de reinitialisation est envoye."}
        if user:
            reset, token = create_password_reset(user)
            payload["expires_at"] = reset.expires_at
            if settings.DEBUG:
                payload["dev_token"] = token
        return Response(payload, status=status.HTTP_201_CREATED)


class PasswordResetConfirmView(APIView):
    """POST /api/auth/password/reset/confirm/."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Mot de passe reinitialise."})


# JWT views (login + refresh) come from SimpleJWT.
LoginView = TokenObtainPairView
RefreshView = TokenRefreshView
