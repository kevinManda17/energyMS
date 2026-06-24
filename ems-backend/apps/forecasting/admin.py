from django.contrib import admin

from .models import Forecast, ImportedModel


@admin.register(ImportedModel)
class ImportedModelAdmin(admin.ModelAdmin):
    list_display = ("name", "target", "model_type", "version", "is_active", "imported_at")
    list_filter = ("target", "model_type", "is_active")
    search_fields = ("name", "file_path", "version")


@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ("target", "house", "forecast_value", "horizon", "model")
    list_filter = ("target", "model")
    search_fields = ("house__name",)

