from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    ChangePasswordSerializer,
    RegisterSerializer,
    SendPhoneCodeSerializer,
    UserSerializer,
    VerifyPhoneCodeSerializer,
)
from .services import create_phone_verification


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


# JWT views (login + refresh) come from SimpleJWT.
LoginView = TokenObtainPairView
RefreshView = TokenRefreshView
