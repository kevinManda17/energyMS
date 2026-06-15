from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("house", "severity", "alert_type", "is_read", "created_at")
    list_filter = ("severity", "is_read", "alert_type")
