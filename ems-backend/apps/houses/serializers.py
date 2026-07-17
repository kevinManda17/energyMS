from rest_framework import serializers

from .models import House


class HouseSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(
        source="owner.username", read_only=True
    )

    class Meta:
        model = House
        fields = (
            "id",
            "owner",
            "owner_username",
            "name",
            "location",
            "latitude",
            "longitude",
            "pv_capacity_kw",
            "battery_capacity_kwh",
            "description",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at")

    def validate_latitude(self, value):
        # La latitude alimente la requête météo Open-Meteo (prévision PV) : une
        # valeur hors bornes fausserait toute la chaîne de décision en silence.
        if value is not None and not (-90.0 <= value <= 90.0):
            raise serializers.ValidationError(
                "La latitude doit être comprise entre -90 et 90."
            )
        return value

    def validate_longitude(self, value):
        if value is not None and not (-180.0 <= value <= 180.0):
            raise serializers.ValidationError(
                "La longitude doit être comprise entre -180 et 180."
            )
        return value
