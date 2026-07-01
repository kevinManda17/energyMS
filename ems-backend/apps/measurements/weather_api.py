"""
Open-Meteo weather/solar API integration.

Fetches current and hourly weather + solar irradiance data for a given location
and stores the values as Measurement records. No API key required.

Variables fetched:
  - shortwave_radiation       → irradiance (W/m²)
  - direct_normal_irradiance  → irradiance direct normal (W/m²)
  - diffuse_radiation         → irradiance diffuse (W/m²)
  - temperature_2m            → temperature (°C)
  - relative_humidity_2m      → humidity (%)
  - surface_pressure          → air_pressure (hPa)
  - wind_speed_10m            → wind_speed (m/s)
  - wind_direction_10m        → wind_direction (°)
"""

import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger("ems.weather_api")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARIABLES = [
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation",
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
]


def fetch_current_weather(latitude: float, longitude: float) -> dict | None:
    """
    Return the most recent hourly weather snapshot for the given coordinates.
    Returns a flat dict of variable → value, or None on failure.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Open-Meteo API error: %s", exc)
        return None

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return None

    now = datetime.now(tz=timezone.utc)
    best_idx = 0
    best_delta = None
    for i, t in enumerate(times):
        try:
            ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        delta = abs((ts - now).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_idx = i

    result = {"_timestamp": times[best_idx]}
    for var in HOURLY_VARIABLES:
        values = hourly.get(var, [])
        result[var] = values[best_idx] if best_idx < len(values) else None
    return result


def fetch_hourly_forecast(latitude: float, longitude: float, hours: int = 24) -> list[dict]:
    """
    Return a list of hourly forecast dicts for the next `hours` hours.
    Each dict contains variable → value plus a 'time' key.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "forecast_days": max(1, (hours // 24) + 1),
        "timezone": "auto",
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Open-Meteo API error: %s", exc)
        return []

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    now = datetime.now(tz=timezone.utc)
    results = []
    for i, t in enumerate(times):
        try:
            ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts <= now:
            continue
        if len(results) >= hours:
            break
        row = {"time": t}
        for var in HOURLY_VARIABLES:
            values = hourly.get(var, [])
            row[var] = values[i] if i < len(values) else None
        results.append(row)
    return results


# Mapping from Open-Meteo variable → (EMS measurement_type, unit)
WEATHER_TO_MEASUREMENT = {
    "shortwave_radiation": ("irradiance", "W/m2"),
    "temperature_2m": ("temperature", "°C"),
    "relative_humidity_2m": ("humidity", "%"),
    "surface_pressure": ("air_pressure", "hPa"),
    "wind_speed_10m": ("wind_speed", "m/s"),
    "wind_direction_10m": ("wind_direction", "°"),
}
