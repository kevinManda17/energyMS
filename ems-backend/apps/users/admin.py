from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import EmailVerificationToken, PasswordResetToken, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "email_verified", "is_staff")
    list_filter = ("role", "email_verified", "is_staff", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (
        ("EMS", {"fields": ("role", "phone", "phone_verified", "email_verified")}),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "used_at", "created_at")
    search_fields = ("user__email", "user__username")


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "used_at", "created_at")
    search_fields = ("user__email", "user__username")
