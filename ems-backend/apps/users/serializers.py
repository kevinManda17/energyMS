from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from rest_framework import serializers

from .models import PhoneVerificationCode

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "phone_verified",
            "preferences",
            "is_admin",
            "created_at",
        )
        read_only_fields = (
            "id",
            "role",
            "phone_verified",
            "is_admin",
            "created_at",
        )

    def update(self, instance, validated_data):
        new_phone = validated_data.get("phone")
        if new_phone is not None and new_phone != instance.phone:
            instance.phone_verified = False
        return super().update(instance, validated_data)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    phone_verification_token = serializers.IntegerField(
        write_only=True, required=False
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone",
            "phone_verification_token",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Les mots de passe ne correspondent pas."}
            )

        phone = attrs.get("phone")
        token = attrs.pop("phone_verification_token", None)
        attrs["_phone_verified"] = False
        if phone:
            if not token:
                raise serializers.ValidationError(
                    {"phone": "Le numero de telephone doit etre verifie."}
                )
            code = (
                PhoneVerificationCode.objects.filter(pk=token, phone=phone)
                .order_by("-created_at")
                .first()
            )
            if not code or not code.is_used or code.is_expired:
                raise serializers.ValidationError(
                    {"phone": "Code de verification invalide ou expire."}
                )
            attrs["_phone_verified"] = True
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        phone_verified = validated_data.pop("_phone_verified", False)
        user = User(**validated_data)
        user.phone_verified = phone_verified
        user.set_password(password)
        user.save()
        return user


class SendPhoneCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=30)


class VerifyPhoneCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=30)
    code = serializers.CharField(min_length=4, max_length=8)

    def validate(self, attrs):
        phone = attrs["phone"]
        code_value = attrs["code"]
        verification = (
            PhoneVerificationCode.objects.filter(phone=phone, used_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not verification or verification.is_expired:
            raise serializers.ValidationError(
                {"code": "Code expire ou introuvable."}
            )
        if verification.attempts >= 5:
            raise serializers.ValidationError(
                {"code": "Nombre de tentatives depasse."}
            )
        verification.attempts += 1
        verification.save(update_fields=["attempts"])
        if not check_password(code_value, verification.code_hash):
            raise serializers.ValidationError({"code": "Code invalide."})
        verification.mark_used()
        attrs["verification"] = verification
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Mot de passe actuel invalide."}
            )
        if attrs["new_password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Les mots de passe ne correspondent pas."}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
