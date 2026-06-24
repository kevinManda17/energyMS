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

    def validate(self, attrs):
        house = attrs.get("house") or getattr(self.instance, "house", None)
        sensor = attrs.get("sensor")
        if sensor is not None and house is not None and sensor.house_id != house.id:
            raise serializers.ValidationError(
                {"sensor": "Le capteur doit appartenir a la meme maison."}
            )
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_admin and house is not None:
            if house.owner_id != user.id:
                raise serializers.ValidationError({"house": "Maison non accessible."})
        return attrs
