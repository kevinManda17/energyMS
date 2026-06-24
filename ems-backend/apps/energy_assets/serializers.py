from rest_framework import serializers

from apps.houses.models import House

from .models import EnergyAsset


class EnergyAssetSerializer(serializers.ModelSerializer):
    house_name = serializers.CharField(source="house.name", read_only=True)

    class Meta:
        model = EnergyAsset
        fields = (
            "id",
            "house",
            "house_name",
            "name",
            "asset_type",
            "nominal_power_kw",
            "capacity_kwh",
            "voltage",
            "current",
            "efficiency",
            "status",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "house_name", "created_at", "updated_at")

    def validate_house(self, house: House) -> House:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_admin and house.owner_id != user.id:
            raise serializers.ValidationError("Maison non accessible.")
        return house

