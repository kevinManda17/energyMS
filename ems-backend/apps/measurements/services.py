"""
Weather collection service.

Shared by the `fetch_weather` management command, the on-demand API endpoint
(POST /api/measurements/weather/collect/) and the periodic background
collector, so all three store exactly the same Measurement records.
"""

import logging
import os
from datetime import datetime, timezone as dt_timezone

from apps.measurements.models import Measurement, Quantity, Source, record
from apps.measurements.weather_api import GTI_UNIT, fetch_solar_snapshot

logger = logging.getLogger("ems.weather")

DEFAULT_LAT = float(os.getenv("WEATHER_LATITUDE", "-4.3276"))
DEFAULT_LON = float(os.getenv("WEATHER_LONGITUDE", "15.3136"))

WEATHER_MEASUREMENT_UNITS = {
    "irradiance": "W/m2",
    "irradiance_tilt15": GTI_UNIT,
    "irradiance_tilt20": GTI_UNIT,
    "irradiance_east": GTI_UNIT,
    "irradiance_west": GTI_UNIT,
    "temperature": "°C",
    "humidity": "%",
    "air_pressure": "hPa",
    "wind_speed": "m/s",
    "wind_direction": "°",
}

# Grandeur typée correspondant à chaque variable renvoyée par Open-Meteo.
# TOUTES sont enregistrées avec `source=WEATHER_API` : ce sont des ESTIMATIONS
# de modèle météorologique, pas des lectures de capteur. La distinction n'est
# pas cosmétique — sans elle, la règle R032 du moteur (« plein soleil mais
# production nulle -> anomalie photovoltaïque ») pouvait diagnostiquer une
# panne matérielle sur la foi d'une irradiance qu'aucun pyranomètre n'avait
# mesurée, sur un prototype qui n'en possède précisément pas.
WEATHER_QUANTITIES = {
    "irradiance": Quantity.IRRADIANCE_WM2,
    "irradiance_tilt15": Quantity.IRRADIANCE_TILT15_WM2,
    "irradiance_tilt20": Quantity.IRRADIANCE_TILT20_WM2,
    "irradiance_east": Quantity.IRRADIANCE_EAST_WM2,
    "irradiance_west": Quantity.IRRADIANCE_WEST_WM2,
    "temperature": Quantity.AMBIENT_TEMP_C,
    "humidity": Quantity.HUMIDITY_PCT,
    "air_pressure": Quantity.AIR_PRESSURE_HPA,
    "wind_speed": Quantity.WIND_SPEED_MS,
    "wind_direction": Quantity.WIND_DIRECTION_DEG,
}

# Measurement types that come from the weather API — used to report the last
# collection time without confusing weather rows with IoT telemetry.
WEATHER_MEASUREMENT_TYPES = list(WEATHER_MEASUREMENT_UNITS)

# Instant of the last successful collection per house id. Open-Meteo snapshots
# are hourly, so the Measurement timestamp alone can't tell "just refreshed"
# from "refreshed 50 minutes ago"; this does (best-effort, reset on restart).
_LAST_COLLECT_AT: dict[int, datetime] = {}


def house_coordinates(house) -> tuple[float, float]:
    lat = getattr(house, "latitude", None)
    lon = getattr(house, "longitude", None)
    return (lat if lat is not None else DEFAULT_LAT,
            lon if lon is not None else DEFAULT_LON)


def collect_weather_for_house(house, lat: float | None = None, lon: float | None = None) -> dict | None:
    """
    Fetch the current Open-Meteo snapshot for the house's coordinates and
    persist each variable as a Measurement. Re-collecting within the same
    hour updates the same rows (update_or_create on house/type/timestamp),
    so frequent collection never duplicates data.

    Returns {"timestamp", "stored", "values"} or None if the fetch failed.
    """
    house_lat, house_lon = house_coordinates(house)
    lat = lat if lat is not None else house_lat
    lon = lon if lon is not None else house_lon

    snapshot = fetch_solar_snapshot(lat, lon)
    if snapshot is None:
        return None

    timestamp_str = snapshot.pop("_timestamp", None)
    try:
        timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=dt_timezone.utc)
    except (TypeError, ValueError):
        timestamp = datetime.now(tz=dt_timezone.utc)

    stored = 0
    values: dict[str, float] = {}
    for mtype, value in snapshot.items():
        if value is None:
            continue
        quantity = WEATHER_QUANTITIES.get(mtype)
        if quantity is None:
            # Une variable sans grandeur connue n'est pas inventee : on la
            # signale et on passe. Lui attribuer une grandeur approchante
            # ferait entrer une donnee mal nommee dans le raisonnement.
            logger.warning("Variable meteo sans grandeur correspondante : %s", mtype)
            continue
        record(house, quantity, float(value), timestamp,
               source=Source.WEATHER_API)
        values[mtype] = float(value)
        stored += 1

    collected_at = datetime.now(tz=dt_timezone.utc)
    _LAST_COLLECT_AT[house.pk] = collected_at
    logger.info("Weather collected for '%s': %d values @ %s", house, stored, timestamp)
    return {
        "timestamp": timestamp,
        "collected_at": collected_at,
        "stored": stored,
        "values": values,
    }


def weather_status_for_house(house) -> dict:
    """
    Last known weather data for this house: hour of the snapshot, instant of
    the last collection (when known in this process), and the latest values.
    """
    rows = Measurement.objects.filter(
        house=house, measurement_type__in=WEATHER_MEASUREMENT_TYPES
    ).order_by("-timestamp")[: len(WEATHER_MEASUREMENT_TYPES)]

    latest_ts = None
    values: dict[str, float] = {}
    for m in rows:
        if latest_ts is None:
            latest_ts = m.timestamp
        if m.timestamp == latest_ts and m.measurement_type not in values:
            values[m.measurement_type] = m.value

    return {
        "house": house.pk,
        "timestamp": latest_ts,
        "collected_at": _LAST_COLLECT_AT.get(house.pk) or latest_ts,
        "values": values,
    }
