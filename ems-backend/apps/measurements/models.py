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
        # ⚠ `temperature` = température AMBIANTE de l'air, alimentée par l'API
        # météo (Open-Meteo, temperature_2m). Ce n'est PAS la température d'une
        # batterie ni d'un panneau : ne jamais l'utiliser comme telle. Les
        # températures d'équipement ont leurs propres types ci-dessous.
        TEMPERATURE = "temperature", "Ambient temperature (weather API)"
        # Températures d'équipement, mesurées par des sondes dédiées (DS18B20).
        # Non installées à ce jour sur le prototype : extension prévue. Tant
        # qu'aucune mesure n'existe, le système expert utilise sa valeur par
        # défaut plutôt que la température ambiante.
        BATTERY_TEMP = "battery_temp", "Battery temperature (probe)"
        PANEL_TEMP = "panel_temp", "Solar panel temperature (probe)"
        # Grandeurs continues du bloc DC, remontées par l'ESP32 secondaire
        # (3 tensions, 3 courants, 3 températures — cf. docs/PROTOCOLE_ESP32.md).
        # Unités : V, A, W. `battery_current` est SIGNÉ, positif = charge :
        # sans le signe, impossible de distinguer une batterie qui se remplit
        # d'une batterie qui se vide, donc impossible de compter les coulombs.
        BATTERY_VOLTAGE = "battery_voltage", "Battery voltage (V)"
        BATTERY_CURRENT = "battery_current", "Battery current, signed (A)"
        BATTERY_POWER = "battery_power", "Battery power (W)"
        # Production photovoltaïque mesurée côté continu, en W. À ne pas
        # confondre avec `production` (kW), qui est l'agrégat applicatif.
        PV_POWER = "pv_power", "PV power, DC side (W)"
        LUMINOSITY = "luminosity", "Luminosity"
        IRRADIANCE = "irradiance", "Irradiance"
        IRRADIANCE_TILT15 = "irradiance_tilt15", "Irradiance inclinee 15°"
        IRRADIANCE_TILT20 = "irradiance_tilt20", "Irradiance inclinee 20°"
        IRRADIANCE_EAST = "irradiance_east", "Irradiance orientee Est"
        IRRADIANCE_WEST = "irradiance_west", "Irradiance orientee Ouest"
        # Electrical grid features (for consumption ML model)
        REACTIVE_POWER = "reactive_power", "Reactive Power"
        SUB_METERING_1 = "sub_metering_1", "Sub-metering 1 (kitchen)"
        SUB_METERING_2 = "sub_metering_2", "Sub-metering 2 (laundry)"
        SUB_METERING_3 = "sub_metering_3", "Sub-metering 3 (HVAC)"
        # PV panel dedicated sensors
        PV_VOLTAGE = "pv_voltage", "PV Voltage (Vmpp)"
        PV_CURRENT = "pv_current", "PV Current (Impp)"
        MODULE_TEMP = "module_temp", "Module Temperature"
        # Weather (from API or sensor)
        HUMIDITY = "humidity", "Relative Humidity"
        AIR_PRESSURE = "air_pressure", "Air Pressure"
        WIND_SPEED = "wind_speed", "Wind Speed"
        WIND_DIRECTION = "wind_direction", "Wind Direction"

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
    # Valeur exploitée par l'application, dans l'unité physique (V, A, kW…).
    # Pour un capteur calibré : raw_value × facteur + offset.
    value = models.FloatField()
    unit = models.CharField(max_length=20, default="kW")
    # Valeur BRUTE remontée par le capteur (RMS en volts ADC), conservée telle
    # quelle. C'est elle qui permet de (re)calculer un coefficient plus tard
    # sans refaire la manipulation physique. Null = mesure sans capteur associé
    # (météo, agrégat calculé…).
    raw_value = models.FloatField(null=True, blank=True)
    # Coefficients réellement utilisés au moment de la mesure : indispensable
    # pour relire un historique après une recalibration, sans le fausser.
    calibration_factor_used = models.FloatField(null=True, blank=True)
    calibration_offset_used = models.FloatField(null=True, blank=True)
    quality_status = models.CharField(max_length=16, blank=True)
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


class LineReading(models.Model):
    """Un relevé électrique, ligne par ligne — la table qui manquait.

    LE DÉFAUT QU'ELLE CORRIGE

    `_store_line_measurements` recevait trois lignes détaillées du nœud et n'en
    gardait que des AGRÉGATS : la somme des puissances, la moyenne des
    tensions, la somme des courants. Le détail par ligne ne survivait que dans
    `RelayState.last_report`, un JSON écrasé toutes les trois secondes.

    Autrement dit : le système mesurait chaque ligne, le moteur raisonnait sur
    chaque ligne, et l'historique n'en gardait aucune trace. On ne pouvait ni
    tracer la courbe d'une ligne, ni calculer son énergie, ni expliquer après
    coup pourquoi l'optimiseur l'avait choisie.

    `is_measured` DISTINGUE « ligne à 0 W » DE « ligne dont on ne sait rien »

    C'est la distinction qu'exige la règle L006 du moteur : une ligne dont les
    capteurs se taisent n'est pas une ligne qui ne consomme rien. Un 0 W
    inventé ferait croire à l'optimiseur qu'il n'a rien à gagner à la couper.

    Les valeurs BRUTES (`raw_voltage`, `raw_current`) et les coefficients
    appliqués sont conservés : ils permettent de recalculer un historique après
    une recalibration sans le fausser — un historique recalibré à partir de
    valeurs déjà calibrées serait faux deux fois.
    """

    line = models.ForeignKey(
        "devices.Line", on_delete=models.CASCADE, related_name="readings"
    )
    timestamp = models.DateTimeField(db_index=True)
    voltage_v = models.FloatField(null=True, blank=True)
    current_a = models.FloatField(null=True, blank=True)
    power_w = models.FloatField(null=True, blank=True)
    relay_closed = models.BooleanField()
    is_measured = models.BooleanField()
    raw_voltage = models.FloatField(null=True, blank=True)
    raw_current = models.FloatField(null=True, blank=True)
    calibration_v = models.FloatField(null=True, blank=True)
    calibration_i = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        constraints = [
            models.UniqueConstraint(
                fields=["line", "timestamp"],
                name="un_releve_par_ligne_et_instant",
            )
        ]
        indexes = [models.Index(fields=["line", "-timestamp"])]

    def __str__(self) -> str:
        puissance = "?" if self.power_w is None else f"{self.power_w:.1f} W"
        return f"{self.line} {puissance} @ {self.timestamp:%Y-%m-%d %H:%M}"
