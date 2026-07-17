from rest_framework import serializers

from apps.energy_assets.models import EnergyAsset

from .models import Equipment, RelayState, Sensor


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


class RelayStateSerializer(serializers.ModelSerializer):
    """État des 3 lignes exposé aux interfaces (le nœud IoT, lui, reçoit du texte)."""

    class Meta:
        model = RelayState
        fields = (
            "line1",
            "line2",
            "line3",
            "control_mode",
            "device_token",
            "last_contact_at",
            "last_report",
            "updated_at",
        )
        # Seuls les états de ligne sont modifiables par l'interface ;
        # le jeton et l'horodatage de contact sont gérés côté serveur.
        read_only_fields = (
            "device_token",
            "last_contact_at",
            "last_report",
            "updated_at",
        )
