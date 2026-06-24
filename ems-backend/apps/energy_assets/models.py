from django.db import models

from apps.houses.models import House


class EnergyAsset(models.Model):
    """Physical energy component attached to a domestic micro-grid."""

    class AssetType(models.TextChoices):
        PV_PANEL = "PV_PANEL", "Panneau photovoltaique"
        BATTERY = "BATTERY", "Batterie"
        INVERTER = "INVERTER", "Onduleur"
        SOLAR_CONTROLLER = "SOLAR_CONTROLLER", "Regulateur solaire"
        GRID_SOURCE = "GRID_SOURCE", "Source reseau"
        GENERATOR = "GENERATOR", "Generateur"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Actif"
        INACTIVE = "INACTIVE", "Inactif"
        FAULT = "FAULT", "Defaillant"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    house = models.ForeignKey(
        House,
        on_delete=models.CASCADE,
        related_name="energy_assets",
    )
    name = models.CharField(max_length=120)
    asset_type = models.CharField(max_length=30, choices=AssetType.choices)
    nominal_power_kw = models.FloatField(null=True, blank=True)
    capacity_kwh = models.FloatField(null=True, blank=True)
    voltage = models.FloatField(null=True, blank=True)
    current = models.FloatField(null=True, blank=True)
    efficiency = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["house", "asset_type", "name"]
        indexes = [
            models.Index(
                fields=["house", "asset_type"],
                name="energy_asse_house_i_7bcaec_idx",
            ),
            models.Index(fields=["status"], name="energy_asse_status_30fcb4_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.asset_type})"
