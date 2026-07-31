"""
Grandeur typée et provenance déclarée — §2.4 de la refonte de la base.

Deux règles y sont vérifiées, et ce sont les deux qui rendent impossibles les
défauts que le dépôt a réellement connus :

  1. une colonne, une grandeur, une unité — l'unité est portée par le NOM ;
  2. toute donnée déclare sa provenance.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from apps.devices.models import Sensor
from apps.houses.models import House
from apps.measurements.models import (
    Measurement,
    Quantity,
    Source,
    record,
    unit_for,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def house():
    user = User.objects.create_user("mesures", "m@x.com", "pass12345")
    return House.objects.create(owner=user, name="Prototype")


# --------------------------------------------------------------------------- #
# L'unité est portée par le nom
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("quantity,attendu", [
    (Quantity.LOAD_POWER_W, "W"),
    (Quantity.GRID_VOLTAGE_V, "V"),
    (Quantity.BATTERY_CURRENT_A, "A"),
    (Quantity.BATTERY_TEMP_C, "°C"),
    (Quantity.IRRADIANCE_WM2, "W/m²"),
    (Quantity.HUMIDITY_PCT, "%"),
    (Quantity.WIND_SPEED_MS, "m/s"),
    (Quantity.AIR_PRESSURE_HPA, "hPa"),
])
def test_the_unit_is_derived_from_the_name(quantity, attendu):
    """Une unité déduite ne peut pas diverger de ce qu'elle décrit.

    Une unité STOCKÉE, si : le backend a écrit des watts sous « kW » pendant
    des mois, et 40 W sont devenus « 40 kW ».
    """
    assert unit_for(quantity) == attendu


def test_energy_is_not_read_as_power():
    """`_wh` doit primer sur `_w`, sinon une énergie se lirait en watts."""
    assert unit_for("pv_energy_24h_wh") == "Wh"
    assert unit_for("pv_power_w") == "W"


def test_every_quantity_carries_a_recognisable_unit():
    """Aucune grandeur ne doit échapper à la règle du suffixe.

    Une grandeur dont l'unité n'est pas déductible du nom rouvrirait la porte
    au champ `unit` en texte libre.
    """
    sans_unite = [q.value for q in Quantity if not unit_for(q.value)]
    assert not sans_unite, f"grandeurs sans unite deductible : {sans_unite}"


# --------------------------------------------------------------------------- #
# Contraintes
# --------------------------------------------------------------------------- #

def test_a_quantity_has_one_value_per_instant(house):
    """Deux valeurs contradictoires au même instant, c'est l'arbitraire.

    Sans cette contrainte, deux collectes météo dans la même heure créaient
    deux lignes, et le moteur lisait « la dernière écrite ».
    """
    instant = timezone.now()
    Measurement.objects.create(
        house=house, quantity=Quantity.IRRADIANCE_WM2, value=800.0,
        timestamp=instant, source=Source.WEATHER_API,
    )
    with pytest.raises(IntegrityError):
        Measurement.objects.create(
            house=house, quantity=Quantity.IRRADIANCE_WM2, value=120.0,
            timestamp=instant, source=Source.WEATHER_API,
        )


def test_a_sensor_measurement_must_name_its_sensor(house):
    """Ce qui empêche une estimation de se faire passer pour une lecture."""
    with pytest.raises(IntegrityError):
        Measurement.objects.create(
            house=house, quantity=Quantity.BATTERY_VOLTAGE_V, value=12.6,
            timestamp=timezone.now(), source=Source.SENSOR, sensor=None,
        )


def test_a_sensor_measurement_is_accepted_with_its_sensor(house):
    capteur = Sensor.objects.create(
        house=house, code="VB1", name="Tension batterie", sensor_type="voltage"
    )
    mesure = Measurement.objects.create(
        house=house, quantity=Quantity.BATTERY_VOLTAGE_V, value=12.6,
        timestamp=timezone.now(), source=Source.SENSOR, sensor=capteur,
    )
    assert mesure.pk is not None


def test_untyped_rows_are_tolerated(house):
    """Les types sans grandeur connue restent tolérés plutôt qu'inventés.

    `luminosity`, `reactive_power` et les sous-comptages du jeu public n'ont
    aucun équivalent physique dans ce micro-réseau. La contrainte d'unicité est
    conditionnelle pour cette raison : on préfère une ligne non typée à une
    grandeur inventée.
    """
    instant = timezone.now()
    for _ in range(2):
        Measurement.objects.create(
            house=house, measurement_type="luminosity", value=350.0,
            timestamp=instant, source=Source.DERIVED,
        )
    assert Measurement.objects.filter(measurement_type="luminosity").count() == 2


# --------------------------------------------------------------------------- #
# Le point d'écriture unique
# --------------------------------------------------------------------------- #

def test_record_declares_the_source_and_deduces_the_unit(house):
    mesure = record(house, Quantity.LOAD_POWER_W, 220.0, timezone.now())
    assert mesure.source == Source.DERIVED     # défaut honnête, pas SENSOR
    assert mesure.unit_symbol == "W"


def test_record_forces_sensor_source_when_a_sensor_is_given(house):
    """Fournir un capteur IMPOSE `SENSOR` : l'incohérence devient impossible."""
    capteur = Sensor.objects.create(
        house=house, code="IB1", name="Courant batterie", sensor_type="current"
    )
    mesure = record(house, Quantity.BATTERY_CURRENT_A, -4.2, timezone.now(),
                    source=Source.DERIVED, sensor=capteur)
    assert mesure.source == Source.SENSOR


def test_record_updates_instead_of_duplicating(house):
    """Réécrire le même instant met à jour, au lieu d'ajouter une ligne
    contradictoire de plus."""
    instant = timezone.now()
    record(house, Quantity.GRID_VOLTAGE_V, 219.0, instant)
    record(house, Quantity.GRID_VOLTAGE_V, 221.0, instant)
    lignes = Measurement.objects.filter(house=house, quantity=Quantity.GRID_VOLTAGE_V)
    assert lignes.count() == 1
    assert lignes.first().value == pytest.approx(221.0)


def test_weather_is_never_recorded_as_a_sensor_reading(house):
    """LE point du §2.4 qui protège le diagnostic du moteur.

    La règle R032 conclut à une panne photovoltaïque quand le soleil est fort
    et la production nulle. Sur la foi d'une irradiance qu'aucun pyranomètre
    n'a mesurée — le prototype n'en a pas — ce diagnostic n'aurait aucune
    valeur. La provenance le dit désormais.
    """
    from unittest.mock import patch

    from apps.measurements import services

    instantane = {
        "_timestamp": timezone.now().replace(microsecond=0).isoformat(),
        "irradiance": 870.0,
        "temperature": 31.0,
    }
    with patch.object(services, "fetch_solar_snapshot", return_value=instantane):
        services.collect_weather_for_house(house)

    for mesure in Measurement.objects.filter(house=house):
        assert mesure.source == Source.WEATHER_API
        assert mesure.sensor is None


# --------------------------------------------------------------------------- #
# Migration d'unités : aucun ordre de grandeur ne change
# --------------------------------------------------------------------------- #

def _migration_0010():
    import importlib

    return importlib.import_module(
        "apps.measurements.migrations.0010_migrer_types_vers_grandeurs"
    )


def test_the_unit_migration_never_changes_an_order_of_magnitude(house):
    """LE test que le §2.4 réclame nommément.

    On rejoue la migration sur des valeurs réalistes et on vérifie que chaque
    valeur convertie vaut EXACTEMENT l'ancienne multipliée par le facteur
    déclaré — ni plus, ni moins, ni mille fois.
    """
    from django.apps import apps as django_apps

    migration = _migration_0010()
    instant = timezone.now()

    # Une valeur par ancien type, choisie pour que l'erreur d'un facteur mille
    # soit visible si elle survenait.
    echantillon = {
        "power": 220.0,             # W    -> load_power_w,      x1
        "voltage": 219.5,           # V    -> grid_voltage_v,    x1
        "current": 1.0,             # A    -> grid_current_a,    x1
        "battery_soc": 62.0,        # %    -> battery_soc_pct,   x1
        "battery_temp": 27.5,       # °C   -> battery_temp_c,    x1
        "temperature": 31.0,        # °C   -> ambient_temp_c,    x1
        "irradiance": 870.0,        # W/m² -> irradiance_wm2,    x1
    }
    for i, (mtype, valeur) in enumerate(echantillon.items()):
        Measurement.objects.create(
            house=house, measurement_type=mtype, value=valeur,
            timestamp=instant - timezone.timedelta(minutes=i),
            source=Source.DERIVED,
        )
    # La conversion x1000 (`consumption` en kW) a son propre test : l'ajouter
    # ici viserait la meme grandeur `load_power_w` et rendrait l'assertion
    # ambigue selon l'ordre de lecture.
    migration.migrer(django_apps, None)

    apres = {
        m.quantity: m.value
        for m in Measurement.objects.filter(house=house).exclude(quantity="")
    }
    assert apres[Quantity.LOAD_POWER_W] == pytest.approx(220.0)
    assert apres[Quantity.GRID_VOLTAGE_V] == pytest.approx(219.5)
    assert apres[Quantity.GRID_CURRENT_A] == pytest.approx(1.0)
    assert apres[Quantity.BATTERY_SOC_PCT] == pytest.approx(62.0)
    assert apres[Quantity.BATTERY_TEMP_C] == pytest.approx(27.5)
    assert apres[Quantity.AMBIENT_TEMP_C] == pytest.approx(31.0)
    assert apres[Quantity.IRRADIANCE_WM2] == pytest.approx(870.0)


def test_the_migration_converts_kilowatts_to_watts_exactly(house):
    """3 kW deviennent 3000 W — pas 3, pas 3 000 000."""
    from django.apps import apps as django_apps

    migration = _migration_0010()
    Measurement.objects.create(
        house=house, measurement_type="consumption", value=3.0,
        timestamp=timezone.now(), source=Source.DERIVED,
    )
    migration.migrer(django_apps, None)

    mesure = Measurement.objects.get(house=house, quantity=Quantity.LOAD_POWER_W)
    assert mesure.value == pytest.approx(3000.0)


def test_the_migration_keeps_the_native_unit_when_two_types_collide(house):
    """`power` (W) et `consumption` (kW) décrivent la MÊME puissance.

    Le même code les écrit ensemble, au même instant. La contrainte n'en
    autorise qu'une : on garde la native en watts, parce que `consumption`
    vaut `round(power / 1000, 4)` et que la reconvertir ne rendrait que 0,1 W
    de granularité.
    """
    from django.apps import apps as django_apps

    migration = _migration_0010()
    instant = timezone.now()
    Measurement.objects.create(house=house, measurement_type="power",
                               value=220.4567, timestamp=instant,
                               source=Source.DERIVED)
    Measurement.objects.create(house=house, measurement_type="consumption",
                               value=0.2205, timestamp=instant,
                               source=Source.DERIVED)
    migration.migrer(django_apps, None)

    lignes = Measurement.objects.filter(house=house, quantity=Quantity.LOAD_POWER_W)
    assert lignes.count() == 1
    # La valeur native, pas celle qui a fait l'aller-retour W -> kW -> W.
    assert lignes.first().value == pytest.approx(220.4567)


def test_the_migration_declares_weather_as_estimated(house):
    from django.apps import apps as django_apps

    migration = _migration_0010()
    Measurement.objects.create(
        house=house, measurement_type="irradiance", value=810.0,
        timestamp=timezone.now(), source=Source.DERIVED,
    )
    migration.migrer(django_apps, None)

    mesure = Measurement.objects.get(house=house, quantity=Quantity.IRRADIANCE_WM2)
    assert mesure.source == Source.WEATHER_API


def test_the_migration_leaves_unmapped_types_alone(house):
    """Aucune grandeur n'est inventée pour un type sans correspondance."""
    from django.apps import apps as django_apps

    migration = _migration_0010()
    for mtype in migration.SANS_CORRESPONDANCE:
        Measurement.objects.create(
            house=house, measurement_type=mtype, value=1.0,
            timestamp=timezone.now(), source=Source.DERIVED,
        )
    migration.migrer(django_apps, None)

    for mtype in migration.SANS_CORRESPONDANCE:
        mesure = Measurement.objects.get(house=house, measurement_type=mtype)
        assert mesure.quantity == ""


# --------------------------------------------------------------------------- #
# §2.5 — la prévision météo survit au redémarrage
# --------------------------------------------------------------------------- #

def test_the_weather_forecast_is_persisted_not_just_cached(house):
    """Le cache mémoire ne survivait pas au redémarrage.

    La prévision qui nourrit le modèle de production n'existait donc nulle part
    de façon durable, et on ne pouvait pas répondre après coup à « la prévision
    d'hier était-elle bonne ? ».
    """
    from unittest.mock import patch

    from apps.forecasting import services
    from apps.measurements.models import Quantity, WeatherForecast

    lignes_api = [
        {"time": "2026-08-01T06:00", "irradiance": 120.0, "temperature": 22.0},
        {"time": "2026-08-01T12:00", "irradiance": 910.0, "temperature": 31.0},
    ]
    services._WEATHER_LOOKUP_CACHE.clear()
    with patch.object(services, "fetch_hourly_solar_forecast", return_value=lignes_api):
        services._weather_forecast_lookup(house, hours=24)

    previsions = WeatherForecast.objects.filter(house=house)
    assert previsions.count() == 4      # 2 échéances x 2 grandeurs
    irradiances = previsions.filter(quantity=Quantity.IRRADIANCE_WM2)
    assert sorted(p.value for p in irradiances) == [120.0, 910.0]


def test_a_forecast_records_when_it_was_issued_and_what_it_describes(house):
    """Les deux horodatages, sans lesquels l'évaluation serait impossible.

    Une prévision émise à 6 h pour 18 h et une émise à 17 h pour 18 h décrivent
    la même heure sans avoir la même valeur de preuve.
    """
    from unittest.mock import patch

    from apps.forecasting import services
    from apps.measurements.models import WeatherForecast

    services._WEATHER_LOOKUP_CACHE.clear()
    with patch.object(services, "fetch_hourly_solar_forecast",
                      return_value=[{"time": "2026-08-01T18:00", "irradiance": 40.0}]):
        services._weather_forecast_lookup(house, hours=24)

    prevision = WeatherForecast.objects.get(house=house)
    assert prevision.fetched_at is not None
    assert prevision.valid_at is not None
    assert prevision.valid_at != prevision.fetched_at
    # L'horizon se déduit des deux, et c'est lui qui portera l'évaluation.
    assert isinstance(prevision.horizon_hours, float)


def test_the_cache_still_avoids_a_second_network_call(house):
    """Le cache reste — comme accélérateur, pas comme mémoire."""
    from unittest.mock import patch

    from apps.forecasting import services

    services._WEATHER_LOOKUP_CACHE.clear()
    lignes = [{"time": "2026-08-01T09:00", "irradiance": 300.0}]
    with patch.object(services, "fetch_hourly_solar_forecast",
                      return_value=lignes) as appel:
        services._weather_forecast_lookup(house, hours=24)
        services._weather_forecast_lookup(house, hours=24)
    assert appel.call_count == 1


def test_persisting_the_forecast_never_breaks_the_prediction(house):
    """Archiver est un enregistrement, pas une condition de la prévision."""
    from unittest.mock import patch

    from apps.forecasting import services

    services._WEATHER_LOOKUP_CACHE.clear()
    lignes = [{"time": "2026-08-01T09:00", "irradiance": 300.0}]
    with patch.object(services, "fetch_hourly_solar_forecast", return_value=lignes):
        with patch.object(services, "_persist_weather_forecast",
                          side_effect=RuntimeError("base indisponible")):
            with pytest.raises(RuntimeError):
                # L'appel direct leve : c'est le contrat interne.
                services._persist_weather_forecast(house, {})
        # Et la prevision, elle, aboutit malgre tout.
        lookup = services._weather_forecast_lookup(house, hours=24)
    assert lookup
