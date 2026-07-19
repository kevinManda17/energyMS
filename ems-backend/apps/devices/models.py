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
    class CalibrationStatus(models.TextChoices):
        UNCALIBRATED = "uncalibrated", "Non calibré"
        CALIBRATED = "calibrated", "Calibré"
        SUSPECT = "suspect", "Suspect (à recalibrer)"

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

    # --- Identité physique -------------------------------------------------
    # Code court et stable, celui qu'on lit sur le montage : V1, I1, V2…
    # C'est la clé utilisée par le nœud ESP32 pour rattacher ses mesures.
    code = models.CharField(max_length=16, blank=True, db_index=True)
    # Ligne AC surveillée (1, 2 ou 3). Null pour un capteur hors ligne (météo…).
    line_number = models.PositiveSmallIntegerField(null=True, blank=True)
    # Broche ESP32 (34, 35, 32, 33, 36, 39) : sert au diagnostic de câblage.
    gpio_pin = models.PositiveSmallIntegerField(null=True, blank=True)
    color = models.CharField(max_length=16, blank=True)
    description = models.TextField(blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    # --- Calibration -------------------------------------------------------
    # valeur_physique = valeur_brute_rms × calibration_factor + calibration_offset
    # Un coefficient PAR capteur : deux ZMPT101B n'ont pas le même potentiomètre.
    # 1.0 / 0.0 = non calibré, on lit alors le RMS brut du capteur (volts ADC).
    calibration_factor = models.FloatField(default=1.0)
    calibration_offset = models.FloatField(default=0.0)
    calibrated_at = models.DateTimeField(null=True, blank=True)
    calibration_method = models.CharField(max_length=120, blank=True)
    # Renseigné par la validation croisée (voir calibration.py) : un capteur dont
    # le coefficient s'écarte trop de ses semblables est signalé, jamais corrigé
    # en douce — c'est au technicien de vérifier le montage.
    calibration_status = models.CharField(
        max_length=16,
        choices=CalibrationStatus.choices,
        default=CalibrationStatus.UNCALIBRATED,
    )

    class Meta:
        ordering = ["house", "line_number", "code", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["house", "code"],
                condition=models.Q(code__gt=""),
                name="unique_sensor_code_per_house",
            )
        ]

    def __str__(self) -> str:
        label = self.code or self.name
        return f"{label} [{self.sensor_type}]"

    @property
    def is_calibrated(self) -> bool:
        """Un capteur laissé à facteur 1.0 / offset 0.0 n'a jamais été calibré."""
        return self.calibrated_at is not None and self.calibration_factor != 1.0

    def apply_calibration(self, raw_value: float | None) -> float | None:
        """Convertit une valeur brute (RMS capteur) en grandeur physique."""
        if raw_value is None:
            return None
        return raw_value * self.calibration_factor + self.calibration_offset


class Equipment(models.Model):
    """Une CHARGE électrique (load) alimentée par une ligne, délestable par l'EMS.

    À ne pas confondre avec les autres objets du système :
      - Sensor      : capteur qui MESURE (V1, I1…) — modèle `Sensor` ;
      - Equipment   : charge qui CONSOMME (lampe, prise) — ce modèle ;
      - RelayState  : organe qui COMMANDE une ligne — modèle `RelayState` ;
      - Measurement : valeur mesurée par un capteur ;
      - la puissance d'une ligne n'est pas mesurée mais CALCULÉE (V × I).

    Plusieurs charges peuvent partager une même ligne (elles sont en parallèle) :
    une ligne ne se réduit donc pas à une charge unique. Couper la ligne 1 coupe
    à la fois la lampe et la prise 1.
    """

    class Priority(models.TextChoices):
        CRITICAL = "CRITICAL", "Critique (à préserver au maximum)"
        IMPORTANT = "IMPORTANT", "Prioritaire"
        NORMAL = "NORMAL", "Normale"
        LOW = "LOW", "Secondaire"
        NON_CRITICAL = "NON_CRITICAL", "Non prioritaire (délestée en premier)"

    class LoadType(models.TextChoices):
        LAMP = "lamp", "Lampe"
        SOCKET = "socket", "Prise"
        APPLIANCE = "appliance", "Appareil"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SHEDDED = "SHEDDED", "Shedded"
        FAULT = "FAULT", "Fault"

    class RelayLine(models.IntegerChoices):
        LINE1 = 1, "Ligne 1"
        LINE2 = 2, "Ligne 2"
        LINE3 = 3, "Ligne 3"

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="equipment"
    )
    name = models.CharField(max_length=120)
    equipment_type = models.CharField(max_length=80, blank=True)
    # Nature de la charge : sert à l'affichage et aux règles (une prise a une
    # consommation variable et inconnue, une lampe est fixe et prévisible).
    load_type = models.CharField(
        max_length=16, choices=LoadType.choices, default=LoadType.OTHER
    )
    # Puissance nominale en kW. 0 = variable/inconnue (cas typique d'une prise).
    rated_power_kw = models.FloatField(default=0)
    priority = models.CharField(
        max_length=15, choices=Priority.choices, default=Priority.NORMAL
    )
    # Ligne physique (relais ESP32) qui alimente cet équipement. Sert au système
    # expert pour savoir QUOI il coupe quand il déleste une ligne : la priorité
    # de chaque ligne est déduite des équipements qui y sont rattachés. Laissé
    # vide = non rattaché ; on retombe alors sur la convention du firmware
    # (L3 prioritaire, L1 moyenne, L2 délestée en premier).
    relay_line = models.IntegerField(
        choices=RelayLine.choices, null=True, blank=True
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
        # Le système expert calcule sa décision et la PROPOSE : elle est mise en
        # attente (auto_pending_lines) et n'est appliquée que si l'utilisateur
        # l'accepte depuis l'interface. Rien n'est coupé sans validation humaine.
        ASSISTED = "ASSISTED", "Assisté (l'expert propose)"
        # Le système expert flou applique lui-même ses décisions automatiques aux
        # lignes, une fois la condition confirmée sur la durée (jamais en mode
        # BLOCKED/RECOMMENDATION, jamais sur des données de mauvaise qualité).
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
