from rest_framework import serializers

from .models import Measurement


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = (
            "id",
            "house",
            "sensor",
            "measurement_type",
            "value",
            "unit",
            "timestamp",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
