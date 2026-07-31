import secrets

from django.conf import settings
from django.db import models

from apps.energy_assets.models import EnergyAsset
from apps.fuzzy_engine.core import priorities as core_priorities
from apps.houses.models import House


def _generate_device_token() -> str:
    """Jeton partagé ESP32 <-> backend (transmis dans l'en-tête X-Device-Token)."""
    return secrets.token_urlsafe(24)


class Priority(models.TextChoices):
    """Priorité d'une charge ou d'une ligne — définie UNE SEULE FOIS.

    Elle était écrite trois fois : dans `Equipment.Priority`, dans
    `core/priorities.py`, et en clair dans les interfaces web et mobile. Les
    trois listes ne coïncidaient pas exactement, ce qui explique le défaut
    d'affichage des priorités : l'interface montrait « prioritaire » là où la
    base disait `IMPORTANT`, et une valeur inconnue tombait dans le vide.

    L'ORDRE suit `core/priorities.PRIORITY_RANK`, du plus délestable au plus
    protégé. Le test `test_priority_enum_matches_the_engine` verrouille cette
    correspondance : le moteur et la base ne peuvent plus diverger sans qu'on
    le voie. Le moteur, lui, reste sans Django — c'est la base qui s'aligne sur
    lui, jamais l'inverse.
    """

    NON_CRITICAL = "NON_CRITICAL", "Non critique"
    LOW = "LOW", "Faible"
    NORMAL = "NORMAL", "Normale"
    IMPORTANT = "IMPORTANT", "Importante"
    CRITICAL = "CRITICAL", "Critique"

    @classmethod
    def ordered(cls) -> list["Priority"]:
        """Du plus délestable au plus protégé, selon le rang du moteur."""
        return sorted(cls, key=lambda p: core_priorities.rank(p.value))


class Line(models.Model):
    """Une ligne électrique commutable — l'entité qui manquait.

    Le moteur expert raisonne LIGNE PAR LIGNE depuis la refonte du système
    expert : il évalue six règles par ligne, et l'optimiseur choisit quelle
    combinaison couper. Mais la ligne n'existait nulle part comme entité. Elle
    était trois colonnes booléennes de `RelayState` (`line1`, `line2`,
    `line3`), un entier sur `Equipment.relay_line`, un autre sur
    `Sensor.line_number`, et une convention dans le firmware.

    Conséquence : rien de ce qui concerne une ligne ne pouvait être ni nommé,
    ni historisé, ni relié. Impossible d'écrire « la ligne 2 a consommé 340 Wh
    hier » — la donnée n'avait pas de sujet à qui appartenir.

    `priority_override` permet de forcer la priorité d'une ligne
    indépendamment des charges qui y sont rattachées. Vide = la priorité se
    déduit des charges, ce qui reste le cas normal.
    """

    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="lines")
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=80)
    # Broche du relais côté ESP32 (25, 26, 27 sur le prototype). Null quand la
    # ligne n'est pas commutable ou que le câblage n'est pas renseigné.
    relay_gpio = models.PositiveSmallIntegerField(null=True, blank=True)
    is_switchable = models.BooleanField(default=True)
    max_power_w = models.FloatField(null=True, blank=True)
    priority_override = models.CharField(
        max_length=16, choices=Priority.choices, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["house", "number"], name="ligne_unique_par_maison"
            )
        ]
        ordering = ["house", "number"]

    def __str__(self) -> str:
        return f"{self.name} (L{self.number})"


class LineState(models.Model):
    """État commandé d'une ligne — remplace les trois booléens de `RelayState`.

    `is_closed` est l'état constaté, `desired_closed` l'état voulu par le
    système expert. Les séparer permet à la fenêtre de confirmation du mode
    automatique de vivre sur la ligne concernée plutôt que dans un JSON global
    (`RelayState.auto_pending_lines`), où l'on ne pouvait pas dire depuis quand
    CETTE ligne-là attendait.
    """

    line = models.OneToOneField(Line, on_delete=models.CASCADE, related_name="state")
    is_closed = models.BooleanField(default=True)
    desired_closed = models.BooleanField(default=True)
    # Depuis quand l'état voulu diffère de l'état constaté. C'est le chrono de
    # la fenêtre de confirmation : on n'agit pas sur un déficit instantané.
    pending_since = models.DateTimeField(null=True, blank=True)
    last_commanded_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="line_updates",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.line}: {'fermée' if self.is_closed else 'ouverte'}"


class IoTNode(models.Model):
    """Un nœud IoT rattaché à un micro-réseau.

    CLÉ ÉTRANGÈRE et non `OneToOne`, délibérément : `RelayState` était en
    `OneToOne` avec `House`, ce qui interdisait structurellement le second nœud
    ESP32 (bloc continu) déjà prévu au protocole, et la passerelle Edge. Un
    micro-réseau a plusieurs interlocuteurs ; le schéma doit le permettre avant
    qu'on en ait besoin, pas après.

    Chaque nœud porte SON jeton : révoquer un nœud compromis n'oblige plus à
    reflasher les autres.
    """

    class NodeType(models.TextChoices):
        ESP32_MAIN = "ESP32_MAIN", "ESP32 principal (lignes AC, relais)"
        ESP32_DC = "ESP32_DC", "ESP32 secondaire (bloc continu)"
        EDGE_GATEWAY = "EDGE_GATEWAY", "Passerelle Edge"

    class ControlMode(models.TextChoices):
        MANUAL = "MANUAL", "Manuel"
        ASSISTED = "ASSISTED", "Assisté (l'expert propose)"
        AUTOMATIC = "AUTOMATIC", "Automatique (expert)"

    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="nodes")
    name = models.CharField(max_length=80, default="ESP32 principal")
    node_type = models.CharField(
        max_length=20, choices=NodeType.choices, default=NodeType.ESP32_MAIN
    )
    device_token = models.CharField(
        max_length=64, unique=True, default=_generate_device_token
    )
    control_mode = models.CharField(
        max_length=16, choices=ControlMode.choices, default=ControlMode.MANUAL
    )
    firmware_version = models.CharField(max_length=30, blank=True)
    last_contact_at = models.DateTimeField(null=True, blank=True)
    last_measurement_at = models.DateTimeField(null=True, blank=True)
    last_report = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["house", "node_type", "name"]

    def __str__(self) -> str:
        return f"{self.name} [{self.node_type}]"


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

    class CalibrationStatus(models.TextChoices):
        UNCALIBRATED = "uncalibrated", "Non calibré"
        CALIBRATED = "calibrated", "Calibré"
        SUSPECT = "suspect", "Suspect (à recalibrer)"

    # `house` et `energy_asset` étaient déclarés DEUX FOIS, de part et d'autre
    # de la classe CalibrationStatus insérée au milieu des champs. Django ne
    # gardait que la seconde déclaration et ignorait silencieusement la
    # première : sans effet en base, mais tout lecteur du modèle devait se
    # demander laquelle faisait foi.
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

    # Alias vers l'énumération unique du module (cf. `Priority` plus haut).
    # Les libellés d'origine (« Critique (à préserver au maximum) »,
    # « Non prioritaire (délestée en premier) ») décrivaient l'EFFET plutôt que
    # le niveau, et divergeaient de ceux affichés par les interfaces. Les
    # libellés vivent désormais en un seul endroit et sont servis par l'API.
    Priority = Priority

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
    # vide = non rattaché ; on retombe alors sur la convention du prototype
    # (L2 prioritaire, L1 et L3 délestables) — cf.
    # apps/fuzzy_engine/core/priorities.py, source de vérité unique.
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
        # Libellé unifié : le backend, le web et le mobile disaient AUTO
        # tandis que le moteur produisait execution_mode = "AUTOMATIC".
        # Deux chaînes pour la même idée obligeaient à traduire mentalement
        # à chaque lecture, et une comparaison distraite les confondait.
        AUTOMATIC = "AUTOMATIC", "Automatique (expert)"

    house = models.OneToOneField(
        House, on_delete=models.CASCADE, related_name="relay_state"
    )
    line1 = models.BooleanField(default=True)
    line2 = models.BooleanField(default=True)
    line3 = models.BooleanField(default=True)
    control_mode = models.CharField(
        max_length=10, choices=ControlMode.choices, default=ControlMode.MANUAL
    )
    # Mode AUTOMATIC : fenêtre de confirmation. Une décision de coupure/rétablissement
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
