from rest_framework import serializers

from .models import Equipment, Sensor


class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = (
            "id",
            "house",
            "name",
            "sensor_type",
            "unit",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "house", "created_at")


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = (
            "id",
            "house",
            "name",
            "equipment_type",
            "rated_power_kw",
            "priority",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
