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


class BatteryState(models.Model):
    """État estimé d'une batterie à un instant donné.

    Séparé de `Measurement` à dessein : une mesure est ce qu'un capteur a lu,
    un `BatteryState` est ce que le système en a DÉDUIT. Le SOC n'est jamais
    mesuré — aucun capteur ne lit « 62 % » — il s'estime, et la méthode
    d'estimation change ce qu'on a le droit d'en faire. Les mettre dans la même
    table aurait effacé cette différence.

    C'est aussi ce qui rend le comptage coulométrique possible : chaque ligne
    part de la précédente, et la chaîne se recale périodiquement sur une
    tension au repos.
    """

    class Method(models.TextChoices):
        # Tension à vide -> table. Valable au repos seulement, +/- 10 %.
        OCV = "OCV", "Tension a vide"
        # Intégration du courant depuis un point recalé. Dérive avec le temps.
        COULOMB = "COULOMB", "Comptage coulometrique"
        # Lecture directe d'un systeme de gestion de batterie.
        BMS = "BMS", "Systeme de gestion de batterie"
        # Aucune méthode applicable. `soc_percent` est alors NULL, et c'est une
        # réponse valide — pas un trou à combler par une valeur plausible.
        UNKNOWN = "UNKNOWN", "Inconnu"

    class Direction(models.TextChoices):
        CHARGE = "CHARGE", "En charge"
        DISCHARGE = "DISCHARGE", "En decharge"
        IDLE = "IDLE", "Au repos"
        UNKNOWN = "UNKNOWN", "Inconnu"

    battery = models.ForeignKey(
        EnergyAsset,
        on_delete=models.CASCADE,
        related_name="battery_states",
        limit_choices_to={"asset_type": EnergyAsset.AssetType.BATTERY},
    )
    timestamp = models.DateTimeField(db_index=True)

    # NULL = inconnu. Surtout pas une valeur par défaut : le moteur doit
    # pouvoir dégrader la qualité des données et bloquer sa décision plutôt
    # que de raisonner sur un chiffre inventé.
    soc_percent = models.FloatField(null=True, blank=True)
    estimation_method = models.CharField(
        max_length=10, choices=Method.choices, default=Method.UNKNOWN
    )
    # Ce que vaut le chiffre. Sans elle, un SOC OCV a +/- 10 % et un SOC BMS a
    # +/- 2 % se ressembleraient trait pour trait.
    uncertainty_percent = models.FloatField(null=True, blank=True)
    # Pourquoi cette methode et pas une autre, en francais.
    estimation_reason = models.TextField(blank=True)

    voltage_v = models.FloatField(null=True, blank=True)
    # Signé : positif = charge, négatif = décharge.
    current_a = models.FloatField(null=True, blank=True)
    temperature_celsius = models.FloatField(null=True, blank=True)
    direction = models.CharField(
        max_length=10, choices=Direction.choices, default=Direction.UNKNOWN
    )

    # Énergies en Wh (cf. §7 : Wh en interne, conversion à l'affichage).
    energy_wh = models.FloatField(null=True, blank=True)
    cumulated_charge_wh = models.FloatField(default=0.0)
    cumulated_discharge_wh = models.FloatField(default=0.0)

    # Dernier recalage du comptage sur une tension au repos. C'est de cet
    # instant que se calcule la dérive annoncée dans `uncertainty_percent`.
    calibrated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["battery", "-timestamp"]),
        ]
        verbose_name = "battery state"
        verbose_name_plural = "battery states"

    def __str__(self) -> str:
        soc = "?" if self.soc_percent is None else f"{self.soc_percent:.0f} %"
        return f"{self.battery_id} SOC={soc} [{self.estimation_method}]"
