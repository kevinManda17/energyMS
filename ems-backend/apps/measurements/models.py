from django.db import models

from apps.devices.models import Sensor
from apps.houses.models import House


class Quantity(models.TextChoices):
    """La grandeur mesurée — et son unité, portée par le NOM.

    LE DÉFAUT CORRIGÉ : `Measurement` avait un `measurement_type` (« power »,
    « consumption », « temperature ») et un champ `unit` en TEXTE LIBRE. Deux
    colonnes pour une seule information, et rien qui garantisse leur accord.
    Le dépôt en porte la cicatrice : le backend a stocké des watts sous l'unité
    « kW » pendant des mois — 40 W devenaient « 40 kW », un facteur mille qui
    faussait le moteur expert et tous les tableaux de bord.

    Une unité en texte libre ne peut pas être fausse « à moitié » : soit elle
    est vérifiée à chaque écriture, soit elle ment un jour. La porter dans le
    nom de la grandeur la rend invérifiable AUTREMENT que juste — on ne peut
    plus écrire des watts dans `pv_power_w` en croyant écrire des kilowatts.

    Deux grandeurs qui ne diffèrent que par l'unité sont donc DEUX grandeurs
    distinctes, jamais une seule avec un champ à côté.
    """

    PV_POWER_W = "pv_power_w", "Puissance PV (W)"
    LOAD_POWER_W = "load_power_w", "Puissance appelée (W)"
    GRID_VOLTAGE_V = "grid_voltage_v", "Tension réseau (V)"
    GRID_CURRENT_A = "grid_current_a", "Courant total (A)"
    BATTERY_VOLTAGE_V = "battery_voltage_v", "Tension batterie (V)"
    BATTERY_CURRENT_A = "battery_current_a", "Courant batterie signé (A)"
    BATTERY_POWER_W = "battery_power_w", "Puissance batterie (W)"
    BATTERY_TEMP_C = "battery_temp_c", "Température batterie (°C)"
    BATTERY_SOC_PCT = "battery_soc_pct", "État de charge (%)"
    PV_VOLTAGE_V = "pv_voltage_v", "Tension PV (V)"
    PV_CURRENT_A = "pv_current_a", "Courant PV (A)"
    MODULE_TEMP_C = "module_temp_c", "Température module (°C)"
    AMBIENT_TEMP_C = "ambient_temp_c", "Température ambiante (°C)"
    IRRADIANCE_WM2 = "irradiance_wm2", "Irradiance globale (W/m²)"
    IRRADIANCE_TILT15_WM2 = "irradiance_tilt15_wm2", "Irradiance inclinée 15° (W/m²)"
    IRRADIANCE_TILT20_WM2 = "irradiance_tilt20_wm2", "Irradiance inclinée 20° (W/m²)"
    IRRADIANCE_EAST_WM2 = "irradiance_east_wm2", "Irradiance orientée est (W/m²)"
    IRRADIANCE_WEST_WM2 = "irradiance_west_wm2", "Irradiance orientée ouest (W/m²)"
    DIFFUSE_WM2 = "diffuse_wm2", "Rayonnement diffus (W/m²)"
    DNI_WM2 = "dni_wm2", "Irradiance directe normale (W/m²)"
    HUMIDITY_PCT = "humidity_pct", "Humidité relative (%)"
    WIND_SPEED_MS = "wind_speed_ms", "Vitesse du vent (m/s)"
    WIND_DIRECTION_DEG = "wind_direction_deg", "Direction du vent (°)"
    AIR_PRESSURE_HPA = "air_pressure_hpa", "Pression atmosphérique (hPa)"


# Unité d'affichage, DÉDUITE du nom de la grandeur. Elle n'est plus stockée :
# une valeur stockée peut diverger de ce qu'elle décrit, une valeur déduite
# non. C'est la seule façon de rendre impossible la répétition du bug ×1000.
_UNITE_PAR_SUFFIXE = {
    "_w": "W", "_wh": "Wh", "_v": "V", "_a": "A", "_c": "°C",
    "_pct": "%", "_wm2": "W/m²", "_ms": "m/s", "_deg": "°", "_hpa": "hPa",
}


def unit_for(quantity: str) -> str:
    """Unité lisible d'une grandeur, déduite du suffixe de son nom."""
    nom = (quantity or "").lower()
    # Du suffixe le plus long au plus court : `_wh` avant `_w`, sinon
    # « energy_wh » se lirait en watts.
    for suffixe in sorted(_UNITE_PAR_SUFFIXE, key=len, reverse=True):
        if nom.endswith(suffixe):
            return _UNITE_PAR_SUFFIXE[suffixe]
    return ""


class Source(models.TextChoices):
    """D'où vient la donnée — ce que le schéma ne disait pas.

    Une irradiance estimée par une API météo et une irradiance lue par un
    pyranomètre étaient jusqu'ici la même ligne dans la même table. Le moteur
    ne pouvait donc pas les distinguer, et la règle R032 (« plein soleil mais
    production nulle -> anomalie photovoltaïque ») pouvait diagnostiquer une
    panne matérielle sur la foi d'une irradiance qu'AUCUN capteur n'avait
    mesurée — sur un prototype qui n'a précisément pas de pyranomètre.

    Un diagnostic ne vaut que ce que vaut sa source.
    """

    SENSOR = "SENSOR", "Mesurée par un capteur"
    WEATHER_API = "WEATHER_API", "Estimée par l'API météo"
    DERIVED = "DERIVED", "Calculée à partir d'autres mesures"
    MANUAL = "MANUAL", "Saisie manuellement"


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
    # La grandeur TYPÉE, unité comprise dans le nom (cf. `Quantity`). Elle
    # remplace le couple (`measurement_type`, `unit`), qui laissait l'unité
    # dériver du sens : le backend a stocké des watts sous « kW » pendant des
    # mois. `measurement_type` subsiste le temps de la bascule des appelants.
    quantity = models.CharField(
        max_length=28, choices=Quantity.choices, blank=True, db_index=True
    )
    # D'OÙ vient la donnée. Une irradiance de l'API météo et une irradiance
    # d'un pyranomètre ne se valent pas : sans ce champ, la règle R032 pouvait
    # diagnostiquer une panne PV sur une irradiance qu'aucun capteur n'a lue.
    # Défaut DERIVED et non SENSOR : une mesure dont l'origine n'est pas
    # déclarée n'est pas une lecture de capteur. Les agrégats du micro-réseau
    # (somme des trois lignes, puissance V x I) sont effectivement calculés.
    # Prendre SENSOR par défaut aurait fait mentir la moitié des lignes.
    source = models.CharField(
        max_length=12, choices=Source.choices, default=Source.DERIVED
    )
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
            models.Index(fields=["house", "quantity", "-timestamp"]),
        ]
        constraints = [
            # Ces deux contraintes sont posées par une migration DISTINCTE,
            # après le remplissage de `quantity` et `source` : les poser avant
            # casserait sur les lignes existantes, dont l'origine n'est pas
            # encore déclarée.
            # Une grandeur ne peut avoir qu'UNE valeur à un instant donné.
            # Sans cette contrainte, deux collectes météo dans la même heure
            # créaient deux lignes contradictoires et le moteur lisait « la
            # dernière écrite », c'est-à-dire l'arbitraire.
            models.UniqueConstraint(
                fields=["house", "quantity", "timestamp"],
                condition=~models.Q(quantity=""),
                name="une_mesure_par_grandeur_et_instant",
            ),
            # Une donnée qui se DIT mesurée doit nommer son capteur. C'est ce
            # qui empêche une estimation de se faire passer pour une lecture.
            models.CheckConstraint(
                check=~models.Q(source=Source.SENSOR) | models.Q(sensor__isnull=False),
                name="mesure_capteur_a_un_capteur",
            ),
        ]

    @property
    def unit_symbol(self) -> str:
        """Unité d'AFFICHAGE, déduite du nom de la grandeur.

        Elle n'est plus stockée : une valeur stockée peut diverger de ce
        qu'elle décrit, une valeur déduite non.
        """
        return unit_for(self.quantity) or self.unit

    def __str__(self) -> str:
        nom = self.quantity or self.measurement_type
        return f"{nom}={self.value}{self.unit_symbol} @ {self.timestamp:%Y-%m-%d %H:%M}"


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


# Ancien type correspondant à chaque grandeur. Il reste écrit le temps que tous
# les lecteurs basculent : `measurement_type` sera retiré quand plus rien ne le
# lira. Écrire les deux permet une bascule sans fenêtre de casse.
#
# Deux grandeurs partagent un ancien type (`load_power_w` était à la fois
# `power` et `consumption`) : on retient celui dont l'unité est NATIVE, pour
# ne pas réintroduire l'aller-retour W -> kW -> W qui coûte de la précision.
LEGACY_TYPE_FOR_QUANTITY = {
    Quantity.PV_POWER_W: "pv_power",
    Quantity.LOAD_POWER_W: "power",
    Quantity.GRID_VOLTAGE_V: "voltage",
    Quantity.GRID_CURRENT_A: "current",
    Quantity.BATTERY_VOLTAGE_V: "battery_voltage",
    Quantity.BATTERY_CURRENT_A: "battery_current",
    Quantity.BATTERY_POWER_W: "battery_power",
    Quantity.BATTERY_TEMP_C: "battery_temp",
    Quantity.BATTERY_SOC_PCT: "battery_soc",
    Quantity.PV_VOLTAGE_V: "pv_voltage",
    Quantity.PV_CURRENT_A: "pv_current",
    Quantity.MODULE_TEMP_C: "module_temp",
    Quantity.AMBIENT_TEMP_C: "temperature",
    Quantity.IRRADIANCE_WM2: "irradiance",
    Quantity.IRRADIANCE_TILT15_WM2: "irradiance_tilt15",
    Quantity.IRRADIANCE_TILT20_WM2: "irradiance_tilt20",
    Quantity.IRRADIANCE_EAST_WM2: "irradiance_east",
    Quantity.IRRADIANCE_WEST_WM2: "irradiance_west",
    Quantity.HUMIDITY_PCT: "humidity",
    Quantity.WIND_SPEED_MS: "wind_speed",
    Quantity.WIND_DIRECTION_DEG: "wind_direction",
    Quantity.AIR_PRESSURE_HPA: "air_pressure",
}


def record(house, quantity, value, timestamp, *, source=Source.DERIVED,
           sensor=None, raw_value=None, **extra):
    """Enregistre UNE mesure — point d'écriture unique.

    Toute écriture passe ici, pour trois raisons :

      - l'unité ne peut plus diverger de la grandeur, puisqu'elle n'est plus
        saisie : elle se déduit du nom (`unit_for`) ;
      - la provenance est explicite à chaque appel. Un capteur fourni impose
        `SENSOR` ; l'oublier ne fait pas passer une estimation pour une lecture ;
      - la contrainte (maison, grandeur, instant) est respectée par
        construction : réécrire le même instant MET À JOUR au lieu de créer une
        ligne contradictoire de plus.
    """
    if sensor is not None:
        source = Source.SENSOR

    defaults = {
        "value": float(value),
        "source": source,
        "sensor": sensor,
        "raw_value": raw_value,
        # `measurement_type` et `unit` restent renseignés le temps de la
        # bascule des lecteurs. Ils ne sont plus la source de vérité.
        "measurement_type": LEGACY_TYPE_FOR_QUANTITY.get(quantity, ""),
        "unit": unit_for(quantity),
        **extra,
    }
    obj, _ = Measurement.objects.update_or_create(
        house=house, quantity=quantity, timestamp=timestamp, defaults=defaults
    )
    return obj


def latest_value(house, quantity, default=None, max_age_seconds=None):
    """Dernière valeur connue d'une grandeur, éventuellement bornée en âge.

    `max_age_seconds` permet à l'appelant de refuser une donnée périmée plutôt
    que de la lire comme si elle décrivait l'instant présent.
    """
    from django.utils import timezone

    qs = Measurement.objects.filter(house=house, quantity=quantity)
    if max_age_seconds is not None:
        limite = timezone.now() - timezone.timedelta(seconds=max_age_seconds)
        qs = qs.filter(timestamp__gte=limite)
    row = qs.order_by("-timestamp").first()
    return row.value if row else default
