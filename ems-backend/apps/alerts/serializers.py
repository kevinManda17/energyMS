from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = (
            "id",
            "house",
            "severity",
            "alert_type",
            "message",
            "is_read",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
