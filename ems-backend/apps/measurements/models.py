from django.db import models

from apps.devices.models import Sensor
from apps.houses.models import House


class Measurement(models.Model):
    """A single IoT measurement point."""

    class Type(models.TextChoices):
        PRODUCTION = "production", "Production"
        CONSUMPTION = "consumption", "Consumption"
        BATTERY_SOC = "battery_soc", "Battery SoC"
        VOLTAGE = "voltage", "Voltage"
        CURRENT = "current", "Current"
        POWER = "power", "Power"
        TEMPERATURE = "temperature", "Temperature"
        LUMINOSITY = "luminosity", "Luminosity"
        IRRADIANCE = "irradiance", "Irradiance"

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="measurements"
    )
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="measurements",
    )
    measurement_type = models.CharField(max_length=20, choices=Type.choices)
    value = models.FloatField()
    unit = models.CharField(max_length=20, default="kW")
    timestamp = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["house", "measurement_type", "-timestamp"]),
            models.Index(
                fields=["sensor", "-timestamp"],
                name="measurement_sensor__8ce9f6_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.measurement_type}={self.value}{self.unit} @ {self.timestamp:%Y-%m-%d %H:%M}"
