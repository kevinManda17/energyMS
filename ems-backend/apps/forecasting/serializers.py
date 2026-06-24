from rest_framework import serializers

from .models import Forecast, ImportedModel


class ImportedModelSerializer(serializers.ModelSerializer):
    algorithm = serializers.SerializerMethodField()

    class Meta:
        model = ImportedModel
        fields = (
            "id",
            "name",
            "target",
            "model_type",
            "algorithm",
            "file",
            "file_path",
            "version",
            "input_schema",
            "metrics",
            "is_active",
            "imported_at",
        )
        read_only_fields = ("id", "imported_at", "algorithm")

    def get_algorithm(self, obj):
        if obj.model_type == "profile":
            return "HourlyProfileForecast"
        return obj.model_type


class ForecastSerializer(serializers.ModelSerializer):
    value = serializers.FloatField(source="forecast_value", read_only=True)
    model_name = serializers.CharField(source="model.name", read_only=True)

    class Meta:
        model = Forecast
        fields = (
            "id",
            "house",
            "model",
            "model_name",
            "target",
            "horizon",
            "horizon_minutes",
            "forecast_value",
            "value",
            "input_snapshot",
            "created_at",
        )
        read_only_fields = fields


# Backward-compatible aliases.
ForecastModelSerializer = ImportedModelSerializer
PredictionSerializer = ForecastSerializer
