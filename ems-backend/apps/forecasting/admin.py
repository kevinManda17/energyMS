from django.contrib import admin

from .models import ForecastModel, Prediction


@admin.register(ForecastModel)
class ForecastModelAdmin(admin.ModelAdmin):
    list_display = ("target", "algorithm", "r2", "mae", "is_active", "created_at")
    list_filter = ("target", "is_active")


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("target", "value", "horizon", "house", "model")
    list_filter = ("target",)
