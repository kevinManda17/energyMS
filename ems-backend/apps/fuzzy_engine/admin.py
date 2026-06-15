from django.contrib import admin

from .models import Decision


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("house", "action", "confidence_score", "created_at")
    list_filter = ("action",)
    date_hierarchy = "created_at"
