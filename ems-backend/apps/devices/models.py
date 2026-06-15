from django.db import models

from apps.houses.models import House


class Sensor(models.Model):
    """A physical/simulated sensor attached to a house."""

    class SensorType(models.TextChoices):
        PRODUCTION = "production", "Production"
        CONSUMPTION = "consumption", "Consumption"
        BATTERY = "battery", "Battery"
        VOLTAGE = "voltage", "Voltage"
        CURRENT = "current", "Current"
        POWER = "power", "Power"
        TEMPERATURE = "temperature", "Temperature"

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="sensors"
    )
    name = models.CharField(max_length=120)
    sensor_type = models.CharField(max_length=20, choices=SensorType.choices)
    unit = models.CharField(max_length=20, default="kW")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["house", "name"]

    def __str__(self) -> str:
        return f"{self.name} [{self.sensor_type}]"


class Equipment(models.Model):
    """An electrical load / appliance that can be shed by the EMS."""

    class Priority(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        IMPORTANT = "IMPORTANT", "Important"
        NORMAL = "NORMAL", "Normal"
        NON_CRITICAL = "NON_CRITICAL", "Non critical"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SHEDDED = "SHEDDED", "Shedded"
        FAULT = "FAULT", "Fault"

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="equipment"
    )
    name = models.CharField(max_length=120)
    equipment_type = models.CharField(max_length=80, blank=True)
    rated_power_kw = models.FloatField(default=0)
    priority = models.CharField(
        max_length=15, choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["house", "name"]
        verbose_name_plural = "equipment"

    def __str__(self) -> str:
        return f"{self.name} [{self.priority}]"
