from django.conf import settings
from django.db import models


class House(models.Model):
    """A home / domestic micro-grid owned by a user."""

    class Status(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        OFFLINE = "OFFLINE", "Offline"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="houses",
    )
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True)
    # Estimated solar configuration — editable at any time (a panel can be
    # added, replaced or re-estimated). Used to scale PV forecasts; when PV
    # panel EnergyAssets carry their own nominal_power_kw, those take
    # precedence over this house-level estimate.
    pv_capacity_kw = models.FloatField(null=True, blank=True)
    battery_capacity_kwh = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.ONLINE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
