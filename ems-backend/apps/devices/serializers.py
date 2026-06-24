from rest_framework import serializers

from apps.energy_assets.models import EnergyAsset

from .models import Equipment, Sensor


class SensorSerializer(serializers.ModelSerializer):
    energy_asset_name = serializers.CharField(
        source="energy_asset.name", read_only=True
    )

    class Meta:
        model = Sensor
        fields = (
            "id",
            "house",
            "energy_asset",
            "energy_asset_name",
            "name",
            "sensor_type",
            "unit",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "house", "created_at")

    def validate_energy_asset(self, energy_asset: EnergyAsset | None):
        if energy_asset is None:
            return energy_asset
        house = self.context.get("house")
        if house is not None and energy_asset.house_id != house.id:
            raise serializers.ValidationError(
                "L'actif energetique doit appartenir a la meme maison."
            )
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_admin:
            if energy_asset.house.owner_id != user.id:
                raise serializers.ValidationError("Actif energetique non accessible.")
        return energy_asset


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
