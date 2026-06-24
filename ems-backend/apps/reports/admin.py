from django.contrib import admin

from .models import DataExport


@admin.register(DataExport)
class DataExportAdmin(admin.ModelAdmin):
    list_display = ("export_type", "house", "user", "created_at")
    list_filter = ("export_type",)
    search_fields = ("house__name", "user__username", "file_path")

