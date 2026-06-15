from rest_framework import serializers

from .models import ForecastModel, Prediction


class ForecastModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastModel
        fields = (
            "id",
            "target",
            "algorithm",
            "mae",
            "rmse",
            "r2",
            "n_samples",
            "is_active",
            "created_at",
        )
        read_only_fields = fields


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = (
            "id",
            "house",
            "model",
            "target",
            "horizon",
            "value",
            "created_at",
        )
        read_only_fields = fields
