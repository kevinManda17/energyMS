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
            "description",
            "pv_capacity_kw",
            "battery_capacity_kwh",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at")
