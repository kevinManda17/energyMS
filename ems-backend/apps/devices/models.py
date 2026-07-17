import secrets

from django.conf import settings
from django.db import models

from apps.energy_assets.models import EnergyAsset
from apps.houses.models import House


def _generate_device_token() -> str:
    """Jeton partagé ESP32 <-> backend (transmis en clair dans l'URL du nœud)."""
    return secrets.token_urlsafe(24)


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
        LUMINOSITY = "luminosity", "Luminosity"
        IRRADIANCE = "irradiance", "Irradiance"

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="sensors"
    )
    energy_asset = models.ForeignKey(
        EnergyAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sensors",
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


class RelayState(models.Model):
    """État commandé des trois lignes électriques du prototype (relais ESP32).

    Le nœud IoT (ESP32 en mode automatique) interroge périodiquement le backend
    et applique ces états sur ses relais (canal 1 -> ligne 1, canal 3 -> ligne 2,
    canal 6 -> ligne 3). Les interfaces web et mobile écrivent ces états ;
    le backend ne fait que les mémoriser puis les restituer au nœud.

    `True`  = ligne alimentée (relais fermé, charge connectée) ;
    `False` = ligne coupée (relais ouvert, charge déconnectée).
    """

    class ControlMode(models.TextChoices):
        # L'humain seul commande les lignes (défaut, comportement historique).
        MANUAL = "MANUAL", "Manuel"
        # Le système expert flou applique ses décisions automatiques aux lignes
        # à chaque sondage du nœud (jamais en mode BLOCKED/RECOMMENDATION, jamais
        # sur une décision issue de données de mauvaise qualité).
        AUTO = "AUTO", "Automatique (expert)"

    house = models.OneToOneField(
        House, on_delete=models.CASCADE, related_name="relay_state"
    )
    line1 = models.BooleanField(default=True)
    line2 = models.BooleanField(default=True)
    line3 = models.BooleanField(default=True)
    control_mode = models.CharField(
        max_length=10, choices=ControlMode.choices, default=ControlMode.MANUAL
    )
    # Mode AUTO : fenêtre de confirmation. Une décision de coupure/rétablissement
    # n'est appliquée aux relais que si elle reste stable pendant EMS_AUTO_
    # CONFIRM_SECONDS — on n'agit pas sur un déficit instantané (transitoire),
    # seulement sur une condition soutenue. `auto_pending_lines` mémorise l'état
    # candidat, `auto_pending_since` l'instant où il est devenu candidat.
    auto_pending_lines = models.JSONField(null=True, blank=True)
    auto_pending_since = models.DateTimeField(null=True, blank=True)
    # Jeton partagé avec le nœud IoT (transmis dans l'URL de sondage HTTP).
    device_token = models.CharField(
        max_length=64, unique=True, default=_generate_device_token
    )
    # Dernier contact du nœud IoT (mis à jour à chaque sondage réussi).
    last_contact_at = models.DateTimeField(null=True, blank=True)
    # Dernière commande envoyée depuis une interface (et non par le nœud).
    # Sert à lier automatiquement un nœud sans jeton au micro-réseau le plus
    # récemment piloté.
    last_commanded_at = models.DateTimeField(null=True, blank=True)
    # Dernier relevé remonté par le nœud (mesures brutes par ligne).
    last_report = models.JSONField(null=True, blank=True)
    # Dernier instant où le relevé du nœud a été persisté comme Measurement
    # (throttle : on ne stocke pas à chaque sondage de 3 s).
    last_measurement_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relay_updates",
    )

    class Meta:
        verbose_name = "relay state"
        verbose_name_plural = "relay states"

    def __str__(self) -> str:
        return f"Relais {self.house_id}: L1={int(self.line1)} L2={int(self.line2)} L3={int(self.line3)}"
