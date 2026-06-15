from django.contrib import admin

from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "status", "rows", "created_at")
    list_filter = ("kind", "status")
