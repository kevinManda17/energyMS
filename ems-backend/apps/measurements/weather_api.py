"""
Open-Meteo weather/solar API integration.

Fetches current and hourly weather + solar irradiance data for a given location
and stores the values as Measurement records. No API key required.

Base hourly variables (single API call):
  - shortwave_radiation       → irradiance (W/m²), i.e. GHI (Global Horizontal Irradiance)
  - direct_normal_irradiance  → irradiance direct normal (W/m²)
  - diffuse_radiation         → irradiance diffuse (W/m²)
  - temperature_2m            → temperature (°C)
  - relative_humidity_2m      → humidity (%)
  - surface_pressure          → air_pressure (hPa)
  - wind_speed_10m            → wind_speed (m/s)
  - wind_direction_10m        → wind_direction (°)

Tilted irradiance (GTI) variables: Open-Meteo only accepts a single tilt/azimuth
pair per request, so each angle below requires its own API call. These map onto
the reference sensor angles used to train the production (PV) model:
  - tilt=15°,  azimuth=0   (south-facing) → irradiance_tilt15
  - tilt=20°,  azimuth=0   (south-facing) → irradiance_tilt20
  - tilt=20°,  azimuth=-90 (east-facing)  → irradiance_east
  - tilt=20°,  azimuth=90  (west-facing)  → irradiance_west

The PV model also expects a "reflected irradiance" pair (G_refl_start/end) and
11 intrinsic electrical-characterization parameters (Isc, Voc, FF, Rsh, Rs,
NRMSE_Isc, R2_Voc, V_ini, I_ini, G_spec_int, APE) that describe the specific
solar cell/module used during training. No public weather API exposes these —
they are properties of the physical hardware, not the weather — so the
forecasting service leaves them to the model's own median imputer.
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

# EMS measurement_type → (tilt degrees, azimuth degrees; 0=south, -90=east, 90=west)
GTI_ANGLES: dict[str, dict[str, float]] = {
    "irradiance_tilt15": {"tilt": 15, "azimuth": 0},
    "irradiance_tilt20": {"tilt": 20, "azimuth": 0},
    "irradiance_east": {"tilt": 20, "azimuth": -90},
    "irradiance_west": {"tilt": 20, "azimuth": 90},
}


def _get(params: dict) -> dict | None:
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Open-Meteo API error: %s", exc)
        return None


def _closest_hour_index(times: list[str]) -> tuple[int, str] | None:
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
    return best_idx, times[best_idx]


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
        "timezone": "UTC",
    }
    data = _get(params)
    if data is None:
        return None

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    picked = _closest_hour_index(times)
    if picked is None:
        return None
    best_idx, best_time = picked

    result = {"_timestamp": best_time}
    for var in HOURLY_VARIABLES:
        values = hourly.get(var, [])
        result[var] = values[best_idx] if best_idx < len(values) else None
    return result


def fetch_tilted_irradiance(latitude: float, longitude: float) -> dict:
    """
    Fetch global tilted irradiance (GTI) at the fixed reference angles used to
    train the production model (see GTI_ANGLES). Issues one API call per angle
    since Open-Meteo only accepts a single tilt/azimuth pair per request.

    Returns a dict of EMS measurement_type → value (missing entries on failure).
    """
    result: dict[str, float] = {}
    for measurement_type, angle in GTI_ANGLES.items():
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "global_tilted_irradiance",
            "tilt": angle["tilt"],
            "azimuth": angle["azimuth"],
            "forecast_days": 1,
            "timezone": "UTC",
        }
        data = _get(params)
        if data is None:
            continue
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        picked = _closest_hour_index(times)
        if picked is None:
            continue
        best_idx, _ = picked
        values = hourly.get("global_tilted_irradiance", [])
        if best_idx < len(values) and values[best_idx] is not None:
            result[measurement_type] = values[best_idx]
    return result


def fetch_solar_snapshot(latitude: float, longitude: float) -> dict | None:
    """
    Combine the base weather snapshot with tilted-irradiance readings into one
    dict of EMS measurement_type → value, ready to persist as Measurements.
    Returns None if the base weather fetch fails (tilted irradiance is
    best-effort and silently omitted on failure).
    """
    base = fetch_current_weather(latitude, longitude)
    if base is None:
        return None

    timestamp = base.pop("_timestamp")
    snapshot: dict[str, float] = {}
    for api_var, (mtype, _unit) in WEATHER_TO_MEASUREMENT.items():
        value = base.get(api_var)
        if value is not None:
            snapshot[mtype] = value

    snapshot.update(fetch_tilted_irradiance(latitude, longitude))
    return {"_timestamp": timestamp, **snapshot}


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
        "timezone": "UTC",
    }
    data = _get(params)
    if data is None:
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


def fetch_hourly_solar_forecast(latitude: float, longitude: float, hours: int = 24) -> list[dict]:
    """
    Return a per-hour forecast series (next `hours` hours) keyed by EMS
    measurement_type, merging the base weather variables and tilted irradiance
    (GTI) onto the same UTC time grid. Used to feed each forecast horizon its
    own expected weather instead of freezing on the last fetched snapshot.

    Each row: {"time": iso_str, "irradiance": ..., "irradiance_tilt15": ..., ...}
    """
    base_rows = fetch_hourly_forecast(latitude, longitude, hours=hours)
    if not base_rows:
        return []

    merged: dict[str, dict] = {}
    for row in base_rows:
        entry = {"time": row["time"]}
        for api_var, (mtype, _unit) in WEATHER_TO_MEASUREMENT.items():
            if row.get(api_var) is not None:
                entry[mtype] = row[api_var]
        merged[row["time"]] = entry

    forecast_days = max(1, (hours // 24) + 1)
    for measurement_type, angle in GTI_ANGLES.items():
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "global_tilted_irradiance",
            "tilt": angle["tilt"],
            "azimuth": angle["azimuth"],
            "forecast_days": forecast_days,
            "timezone": "UTC",
        }
        data = _get(params)
        if data is None:
            continue
        hourly = data.get("hourly", {})
        for t, v in zip(hourly.get("time", []), hourly.get("global_tilted_irradiance", [])):
            if t in merged and v is not None:
                merged[t][measurement_type] = v

    return [merged[t] for t in sorted(merged)]


# Mapping from Open-Meteo variable → (EMS measurement_type, unit)
WEATHER_TO_MEASUREMENT = {
    "shortwave_radiation": ("irradiance", "W/m2"),
    "temperature_2m": ("temperature", "°C"),
    "relative_humidity_2m": ("humidity", "%"),
    "surface_pressure": ("air_pressure", "hPa"),
    "wind_speed_10m": ("wind_speed", "m/s"),
    "wind_direction_10m": ("wind_direction", "°"),
}

# Units for the tilted-irradiance measurement types (all W/m²).
GTI_UNIT = "W/m2"
