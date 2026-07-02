"""
Forecasting service for EMS inference.

Supports three inference backends:
  1. Keras sequence models (GRU, LSTM, CNN-LSTM, LSTM-Attention)
     with separate preprocessing.joblib (imputer + scalers).
  2. Scikit-learn pipelines stored as .joblib.
  3. Hourly profile fallback (mathematical solar/consumption model).

Both the GRU (consumption) and the historical PV Keras/RF models were
trained on 10-minute-cadence telemetry to predict a single next step
(target_next_global_active_power / target_next_Pmpp) — not "the value one
hour from now". predict_future() honours that by generating points on a
`step_minutes` grid (default 10, matching training) instead of hourly
buckets.

Consumption inference flow (GRU, autoregressive rollout — see
_rollout_consumption_gru):
  - Build the initial `sequence_length`-step window from real Measurement
    history, resampled onto the model's true step_minutes grid (hold-last-
    known-value), with each row's temporal features (hour/dayofweek/month/
    is_weekend) computed from that row's OWN timestamp.
  - Predict the next step, append it to the window, drop the oldest step,
    advance the clock by step_minutes, repeat. Each point genuinely depends
    on the previous prediction, so values evolve instead of repeating.

Production inference (Random Forest, flat per-step — see
_predict_pv_sklearn): the RF has no historical window at all — each
horizon's prediction comes straight from that horizon's own forecasted
weather + last known panel electricals, so it can't suffer the "frozen
window" repetition failure sequence models have when reused across many
horizons.
"""
from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timedelta

import joblib
import numpy as np
from django.utils import timezone

from apps.energy_assets.models import EnergyAsset
from apps.measurements.models import Measurement
from apps.measurements.weather_api import fetch_hourly_solar_forecast

from .models import Forecast, ImportedModel

logger = logging.getLogger("ems.forecasting")

VALID_TARGETS = {"production", "consumption"}
BASELINE_ALGORITHM = "HourlyProfileForecast"
PROFILE_MODEL_TYPE = "profile"
KERAS_MODEL_TYPES = {"keras_gru", "keras_lstm", "keras_cnn_lstm", "keras_lstm_att"}

# Native step of the underlying models (trained on 10-minute telemetry to
# predict a single next step). Callers may request a coarser step_minutes,
# but this is the default and the grid the GRU rollout reasons in.
DEFAULT_STEP_MINUTES = 10
MAX_STEPS = 576  # safety cap regardless of hours/step_minutes combination

# --------------------------------------------------------------------------- #
# Feature mapping: EMS measurement_type → consumption model feature column
# --------------------------------------------------------------------------- #
CONSUMPTION_FEATURE_MAP: dict[str, str] = {
    "Global_active_power": "consumption",
    "Global_reactive_power": "reactive_power",
    "Voltage": "voltage",
    "Global_intensity": "current",
    "Sub_metering_1": "sub_metering_1",
    "Sub_metering_2": "sub_metering_2",
    "Sub_metering_3": "sub_metering_3",
}
CONSUMPTION_TARGET_COLUMN = "Global_active_power"
CONSUMPTION_TEMPORAL = ["hour", "dayofweek", "month", "is_weekend"]

# --------------------------------------------------------------------------- #
# Feature mapping: EMS measurement_type → PV model feature column
#
# G_refl_start/end (ground-reflected irradiance) and the 11 intrinsic
# electrical-characterization parameters (Isc, Voc, FF, Rsh, Rs, NRMSE_Isc,
# R2_Voc, V_ini, I_ini, G_spec_int, APE) describe the specific solar cell used
# during training, not the weather — no public API exposes them, so they are
# intentionally left unmapped and filled by the model's own median imputer.
# --------------------------------------------------------------------------- #
PV_FEATURE_MAP: dict[str, str] = {
    "Pmpp": "production",          # production stored in kW; multiply × 1000 → W
    "Vmpp": "pv_voltage",
    "Impp": "pv_current",
    "module_temperature_center": "module_temp",
    "module_temperature_lateral": "module_temp",
    "air_temperature": "temperature",
    "relative_humidity": "humidity",
    "abs_pressure": "air_pressure",
    "wind_speed_ms": "wind_speed",
    "wind_direction": "wind_direction",
    "G_horiz_start": "irradiance",
    "G_horiz_end": "irradiance",
    "G_tilt15_start": "irradiance_tilt15",
    "G_tilt15_end": "irradiance_tilt15",
    "G_tilt20_start": "irradiance_tilt20",
    "G_tilt20_end": "irradiance_tilt20",
    "G_east_start": "irradiance_east",
    "G_east_end": "irradiance_east",
    "G_west_start": "irradiance_west",
    "G_west_end": "irradiance_west",
}

# Feature columns fed from the weather API forecast (rather than past device
# telemetry) — overridden per-horizon so production varies through the day
# instead of freezing on the last fetched snapshot (mirrors CONSUMPTION_TEMPORAL).
PV_WEATHER_MEASUREMENT_TYPES = {
    "irradiance", "irradiance_tilt15", "irradiance_tilt20",
    "irradiance_east", "irradiance_west",
    "temperature", "humidity", "air_pressure", "wind_speed", "wind_direction",
}


# =========================================================================== #
# Profile / fallback models                                                     #
# =========================================================================== #

def get_or_create_profile_model(target: str) -> ImportedModel:
    model = ImportedModel.objects.filter(
        target=target, model_type=PROFILE_MODEL_TYPE, is_active=True
    ).first()
    if model:
        return model
    return ImportedModel.objects.create(
        name=f"{BASELINE_ALGORITHM} {target}",
        target=target,
        model_type=PROFILE_MODEL_TYPE,
        file_path=f"internal://{BASELINE_ALGORITHM.lower()}/{target}",
        version="fallback",
        input_schema={"features": ["hour", "recent_production_kw", "recent_consumption_kw",
                                   "battery_soc", "pv_nominal_power_kw"]},
        metrics={},
        is_active=True,
    )


def get_or_create_forecast_model(target: str) -> ImportedModel:
    return get_or_create_profile_model(target)


def _active_keras_model(target: str) -> ImportedModel | None:
    return (
        ImportedModel.objects.filter(target=target, is_active=True,
                                     model_type__in=KERAS_MODEL_TYPES)
        .order_by("-imported_at")
        .first()
    )


def _active_sklearn_model(target: str) -> ImportedModel | None:
    return (
        ImportedModel.objects.filter(target=target, is_active=True, model_type="sklearn")
        .order_by("-imported_at")
        .first()
    )


# =========================================================================== #
# Helper utilities                                                              #
# =========================================================================== #

def pv_nominal_power_kw(house, fallback: float = 5.0) -> float:
    if house is None:
        return fallback
    total = (
        EnergyAsset.objects.filter(
            house=house,
            asset_type=EnergyAsset.AssetType.PV_PANEL,
            status=EnergyAsset.Status.ACTIVE,
        )
        .exclude(nominal_power_kw__isnull=True)
        .values_list("nominal_power_kw", flat=True)
    )
    capacity = sum(float(v or 0) for v in total)
    return capacity or fallback


def _recent_average(house, measurement_type: str, fallback: float) -> float:
    if house is None:
        return fallback
    values = list(
        Measurement.objects.filter(house=house, measurement_type=measurement_type)
        .order_by("-timestamp")
        .values_list("value", flat=True)[:24]
    )
    return max(0.0, sum(float(v) for v in values) / len(values)) if values else fallback


def _solar_profile(hour: int, pv_capacity_kw: float) -> float:
    return max(0.0, math.sin((hour - 6) / 12 * math.pi) * pv_capacity_kw)


def _consumption_profile(hour: int, recent_avg_kw: float) -> float:
    morning = math.exp(-((hour - 7) ** 2) / 8)
    evening = math.exp(-((hour - 20) ** 2) / 8)
    return max(0.15, recent_avg_kw * (0.65 + 0.75 * morning + 1.05 * evening))


def _house_coordinates(house) -> tuple[float, float]:
    default_lat = float(os.getenv("WEATHER_LATITUDE", "-4.3276"))
    default_lon = float(os.getenv("WEATHER_LONGITUDE", "15.3136"))
    if house is None:
        return default_lat, default_lon
    return house.latitude or default_lat, house.longitude or default_lon


_WEATHER_LOOKUP_CACHE: dict[tuple[float, float, int], tuple[float, dict[datetime, dict]]] = {}
_WEATHER_LOOKUP_TTL_SECONDS = 600  # Open-Meteo's own hourly data doesn't change faster than this;
                                   # avoids a ~12s round-trip (5 sequential HTTP calls) on every
                                   # forecast request, e.g. while a user pages through results.


def _weather_forecast_lookup(house, hours: int) -> dict[datetime, dict]:
    """
    Fetch the hourly weather/irradiance forecast for the house's location once
    and index it by hour (naive UTC, matching Django's TIME_ZONE=UTC), so each
    forecast horizon can look up its own expected weather instead of reusing
    whatever was last fetched into the Measurement table. Open-Meteo only
    returns hourly data, so sub-hour horizons (step_minutes < 60) reuse the
    same hour's weather for every step inside that hour.
    """
    lat, lon = _house_coordinates(house)
    cache_key = (round(lat, 3), round(lon, 3), hours)
    cached = _WEATHER_LOOKUP_CACHE.get(cache_key)
    now_ts = timezone.now().timestamp()
    if cached and now_ts - cached[0] < _WEATHER_LOOKUP_TTL_SECONDS:
        return cached[1]

    try:
        rows = fetch_hourly_solar_forecast(lat, lon, hours=hours)
    except Exception as exc:
        logger.warning("Weather forecast fetch failed: %s", exc)
        return cached[1] if cached else {}

    lookup: dict[datetime, dict] = {}
    for row in rows:
        try:
            ts = datetime.fromisoformat(row["time"]).replace(minute=0, second=0, microsecond=0)
        except (KeyError, ValueError):
            continue
        lookup[ts] = row
    _WEATHER_LOOKUP_CACHE[cache_key] = (now_ts, lookup)
    return lookup


def _weather_row_for_horizon(weather_lookup: dict[datetime, dict], horizon: datetime) -> dict | None:
    """
    Open-Meteo only returns hourly weather, so every sub-hour horizon
    (step_minutes < 60) would otherwise reuse the exact same reading as its
    5 neighbours within that hour, making a flat-model like the production RF
    output identical values 6 times in a row. Linearly interpolating between
    the two surrounding hourly readings keeps each 10-minute step genuinely
    distinct without fabricating the underlying weather data.
    """
    naive_horizon = horizon.replace(second=0, microsecond=0, tzinfo=None)
    floor_hour = naive_horizon.replace(minute=0)
    row_floor = weather_lookup.get(floor_hour)
    if naive_horizon.minute == 0 or row_floor is None:
        return row_floor
    row_ceil = weather_lookup.get(floor_hour + timedelta(hours=1))
    if row_ceil is None:
        return row_floor
    frac = naive_horizon.minute / 60.0
    merged = dict(row_floor)
    for key, val_floor in row_floor.items():
        val_ceil = row_ceil.get(key)
        if isinstance(val_floor, (int, float)) and isinstance(val_ceil, (int, float)):
            merged[key] = val_floor + (val_ceil - val_floor) * frac
    return merged


def _feature_context(house, horizon) -> dict:
    capacity = pv_nominal_power_kw(house)
    return {
        "hour": horizon.hour,
        "weekday": horizon.weekday(),
        "recent_production_kw": _recent_average(house, "production", fallback=capacity * 0.35),
        "recent_consumption_kw": _recent_average(house, "consumption", fallback=1.8),
        "battery_soc": _recent_average(house, "battery_soc", fallback=50.0),
        "pv_nominal_power_kw": capacity,
    }


def _apply_production_night_zero(target: str, horizon, weather_row: dict | None, value: float) -> float:
    """
    Zero out production forecasts at night, using this horizon's own
    forecasted irradiance when available (falls back to a fixed
    daylight-hours heuristic otherwise). Applied uniformly regardless of
    which backend (Keras, sklearn, profile) produced the raw value.
    """
    if target != "production":
        return value
    horizon_irr = weather_row.get("irradiance") if weather_row else None
    if horizon_irr is not None:
        return 0.0 if horizon_irr <= 0 else value
    if not (5 <= horizon.hour <= 19):
        return 0.0
    return value


# =========================================================================== #
# Model artifact caching (avoid reloading .keras / .joblib on every horizon)   #
# =========================================================================== #

_keras_model_cache: dict[int, tuple[float, object]] = {}
_keras_prep_cache: dict[int, tuple[float, dict]] = {}
_sklearn_artifact_cache: dict[int, tuple[float, object]] = {}


def _load_keras_preprocessing(model_record: ImportedModel) -> dict | None:
    """Load preprocessing.joblib; returns None on failure."""
    path = model_record.preprocessing_path
    if not path or not os.path.exists(path):
        logger.warning("preprocessing_path missing or not found: %s", path)
        return None
    try:
        return joblib.load(path)
    except Exception as exc:
        logger.warning("Cannot load preprocessing: %s", exc)
        return None


def _load_keras_model(model_record: ImportedModel):
    """Load the Keras model; returns None on failure."""
    path = model_record.resolved_path
    if not path or not os.path.exists(path):
        logger.warning("Model file not found: %s", path)
        return None
    try:
        import tensorflow as tf  # noqa: F401 – lazy import
        from tensorflow import keras
        return keras.models.load_model(path)
    except Exception as exc:
        logger.warning("Cannot load Keras model: %s", exc)
        return None


def _get_keras_model_cached(model_record: ImportedModel):
    path = model_record.resolved_path
    if not path or not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    cached = _keras_model_cache.get(model_record.pk)
    if cached and cached[0] == mtime:
        return cached[1]
    model = _load_keras_model(model_record)
    if model is not None:
        _keras_model_cache[model_record.pk] = (mtime, model)
    return model


def _get_keras_preprocessing_cached(model_record: ImportedModel) -> dict | None:
    path = model_record.preprocessing_path
    if not path or not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    cached = _keras_prep_cache.get(model_record.pk)
    if cached and cached[0] == mtime:
        return cached[1]
    prep = _load_keras_preprocessing(model_record)
    if prep is not None:
        _keras_prep_cache[model_record.pk] = (mtime, prep)
    return prep


def _get_sklearn_artifact_cached(model_record: ImportedModel):
    path = model_record.resolved_path
    if not path or path.startswith("internal://") or not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    cached = _sklearn_artifact_cache.get(model_record.pk)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        artifact = joblib.load(path)
    except Exception as exc:
        logger.warning("Cannot load sklearn artifact: %s", exc)
        return None
    _sklearn_artifact_cache[model_record.pk] = (mtime, artifact)
    return artifact


def _fetch_recent_measurements(house, mtype: str, n: int) -> list[float]:
    """Return the last `n` values for a given measurement type, oldest first."""
    qs = (
        Measurement.objects.filter(house=house, measurement_type=mtype)
        .order_by("-timestamp")
        .values_list("value", flat=True)[:n]
    )
    return list(reversed(list(qs)))


def _resample_last_known(house, mtype: str, timestamps: list[datetime]) -> list[float | None]:
    """
    For each timestamp (ascending), return the most recent real measurement
    value at or before it ("hold last known value"), or None if no
    measurement exists yet at that point in time. Lets the model window be
    built on its true step_minutes grid even though real telemetry in this
    deployment currently arrives hourly (or sparser).
    """
    if not timestamps or house is None:
        return [None] * len(timestamps)
    rows = list(
        Measurement.objects.filter(
            house=house, measurement_type=mtype, timestamp__lte=timestamps[-1]
        )
        .order_by("-timestamp")
        .values_list("timestamp", "value")[:500]
    )
    rows.reverse()  # ascending

    result: list[float | None] = []
    idx = 0
    last_value: float | None = None
    for ts in timestamps:
        while idx < len(rows) and rows[idx][0] <= ts:
            last_value = float(rows[idx][1])
            idx += 1
        result.append(last_value)
    return result


def _temporal_features(ts: datetime) -> dict[str, float]:
    return {
        "hour": float(ts.hour),
        "dayofweek": float(ts.weekday()),
        "month": float(ts.month),
        "is_weekend": float(1 if ts.weekday() >= 5 else 0),
    }


# =========================================================================== #
# Consumption: GRU autoregressive rollout                                       #
# =========================================================================== #

def _consumption_window_timestamps(now: datetime, seq_len: int, step_minutes: int) -> list[datetime]:
    return [now - timedelta(minutes=step_minutes * (seq_len - i)) for i in range(seq_len)]


def _build_consumption_window(
    house, feature_cols: list[str], timestamps: list[datetime]
) -> list[list[float | None]]:
    """
    Build seq_len rows x n_features. Unlike a single frozen horizon, each
    row's temporal features (hour/dayofweek/month/is_weekend) are computed
    from that row's OWN timestamp — training data never has 36 consecutive
    steps that all claim to be the same hour, so neither should inference.
    """
    series_cache: dict[str, list[float | None]] = {}
    for col in feature_cols:
        if col in CONSUMPTION_TEMPORAL:
            continue
        mtype = CONSUMPTION_FEATURE_MAP.get(col)
        if mtype is None:
            continue
        series_cache[col] = _resample_last_known(house, mtype, timestamps)

    rows: list[list[float | None]] = []
    for row_idx, ts in enumerate(timestamps):
        temporal = _temporal_features(ts)
        row: list[float | None] = []
        for col in feature_cols:
            if col in CONSUMPTION_TEMPORAL:
                row.append(temporal[col])
            else:
                row.append(series_cache.get(col, [None] * len(timestamps))[row_idx])
        rows.append(row)
    return rows


def _rollout_consumption_gru(
    model_record: ImportedModel, house, now: datetime, n_steps: int, step_minutes: int
) -> list[dict] | None:
    """
    Genuine multi-step forecast: predict the next step, feed it back into the
    window, advance the clock by step_minutes, repeat. Returns None (caller
    falls back to the frozen-window single-shot path) if the model or its
    preprocessing can't be loaded.
    """
    prep = _get_keras_preprocessing_cached(model_record)
    if prep is None:
        return None
    keras_model = _get_keras_model_cached(model_record)
    if keras_model is None:
        return None

    seq_len = prep.get("sequence_length", 36)
    feature_cols: list[str] = prep.get("feature_columns", [])
    if not feature_cols or CONSUMPTION_TARGET_COLUMN not in feature_cols:
        return None
    target_idx = feature_cols.index(CONSUMPTION_TARGET_COLUMN)

    imputer = prep.get("feature_imputer")
    x_scaler = prep.get("x_scaler")
    y_scaler = prep.get("y_scaler")

    window_timestamps = _consumption_window_timestamps(now, seq_len, step_minutes)
    window = _build_consumption_window(house, feature_cols, window_timestamps)

    # Last known real value for every non-temporal, non-target column, held
    # constant going forward — the model only forecasts Global_active_power,
    # so the other channels (voltage, sub-metering...) aren't independently
    # projected (same simplification the training pipeline's median-fill made
    # for genuinely missing data).
    held_values: dict[int, float | None] = {}
    for col_idx, col in enumerate(feature_cols):
        if col in CONSUMPTION_TEMPORAL or col_idx == target_idx:
            continue
        held_values[col_idx] = next(
            (row[col_idx] for row in reversed(window) if row[col_idx] is not None), None
        )

    results: list[dict] = []
    for step in range(1, n_steps + 1):
        horizon = now + timedelta(minutes=step_minutes * step)

        X = np.array(
            [[v if v is not None else np.nan for v in row] for row in window], dtype=float
        )
        if imputer:
            X = imputer.transform(X)
        X_scaled = x_scaler.transform(X) if x_scaler is not None else X

        try:
            y_pred_scaled = keras_model.predict(X_scaled[np.newaxis, :, :], verbose=0)
            raw = (
                float(y_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1))[0, 0])
                if y_scaler is not None
                else float(y_pred_scaled.reshape(-1)[0])
            )
        except Exception as exc:
            logger.warning("GRU rollout inference error at step %s: %s", step, exc)
            return results or None

        value = round(max(0.0, raw), 4)

        new_row: list[float | None] = [None] * len(feature_cols)
        temporal = _temporal_features(horizon)
        for col_idx, col in enumerate(feature_cols):
            if col in CONSUMPTION_TEMPORAL:
                new_row[col_idx] = temporal[col]
            elif col_idx == target_idx:
                new_row[col_idx] = raw
            else:
                new_row[col_idx] = held_values.get(col_idx)
        window.pop(0)
        window.append(new_row)

        results.append({
            "horizon": horizon,
            "horizon_minutes": step_minutes * step,
            "forecast_value": value,
            "value": value,
            "model": model_record,
            "input_snapshot": {
                "mode": model_record.model_type,
                "rollout_step": step,
                "step_minutes": step_minutes,
            },
        })
    return results


# =========================================================================== #
# Keras single-shot inference (PV fallback; consumption fallback if rollout    #
# preprocessing/model can't be loaded)                                         #
# =========================================================================== #

def _build_consumption_sequence(house, prep: dict, horizon) -> np.ndarray | None:
    """Single-shot fallback (frozen window) used only if the autoregressive
    rollout can't run (e.g. preprocessing missing sequence_length)."""
    seq_len = prep.get("sequence_length", 36)
    feature_cols: list[str] = prep.get("feature_columns", [])
    if not feature_cols:
        return None

    timestamps = _consumption_window_timestamps(horizon, seq_len, DEFAULT_STEP_MINUTES)
    rows = _build_consumption_window(house, feature_cols, timestamps)
    X = np.array([[v if v is not None else np.nan for v in row] for row in rows], dtype=float)

    imputer = prep.get("feature_imputer")
    x_scaler = prep.get("x_scaler")
    if imputer:
        X = imputer.transform(X)
    if x_scaler:
        X = x_scaler.transform(X)

    return X[np.newaxis, :, :]


def _build_pv_sequence(house, prep: dict, horizon, weather_row: dict | None = None) -> np.ndarray | None:
    """
    Build a (1, sequence_length, n_features) array for the PV LSTM.
    Features not available from DB are filled by the median imputer (same as training).

    `weather_row` (EMS measurement_type → value) is the forecast for this
    specific horizon; when present, irradiance/temperature/humidity/pressure/
    wind columns are overridden with it across the whole sequence window
    (same pattern as CONSUMPTION_TEMPORAL) so production tracks the expected
    weather at that hour instead of freezing on the most recent DB snapshot.
    """
    seq_len = prep.get("sequence_length", 36)
    feature_cols: list[str] = prep.get("feature_columns", [])
    if not feature_cols:
        return None

    rows: list[list[float | None]] = []
    for _ in range(seq_len):
        rows.append([None] * len(feature_cols))

    for col_idx, col in enumerate(feature_cols):
        mtype = PV_FEATURE_MAP.get(col)
        if mtype is None:
            continue
        if mtype in PV_WEATHER_MEASUREMENT_TYPES and weather_row and weather_row.get(mtype) is not None:
            value = float(weather_row[mtype])
            for row_idx in range(seq_len):
                rows[row_idx][col_idx] = value
            continue
        values = _fetch_recent_measurements(house, mtype, seq_len)
        # PV production in EMS is kW; model expects Watts
        if col == "Pmpp":
            values = [v * 1000.0 for v in values]
        for row_offset, val in enumerate(values):
            actual_row = seq_len - len(values) + row_offset
            rows[actual_row][col_idx] = float(val)

    X = np.array(rows, dtype=float)  # (seq_len, n_features) — NaN filled by imputer

    imputer = prep.get("feature_imputer")
    x_scaler = prep.get("x_scaler")
    if imputer:
        X = imputer.transform(X)
    if x_scaler:
        X = x_scaler.transform(X)

    return X[np.newaxis, :, :]  # (1, seq_len, n_features)


def _predict_with_keras_model(
    model_record: ImportedModel,
    house,
    horizon,
    target: str,
    weather_row: dict | None = None,
) -> float | None:
    """
    Single-shot Keras inference for one horizon (frozen window). Used as a
    fallback when the autoregressive rollout isn't available, and for the PV
    Keras model when it's the active model for production.
    Returns the predicted value in kW, or None on any failure.
    """
    prep = _get_keras_preprocessing_cached(model_record)
    if prep is None:
        return None

    keras_model = _get_keras_model_cached(model_record)
    if keras_model is None:
        return None

    if target == "consumption":
        X = _build_consumption_sequence(house, prep, horizon)
    else:
        X = _build_pv_sequence(house, prep, horizon, weather_row=weather_row)

    if X is None:
        return None

    try:
        y_pred_scaled = keras_model.predict(X, verbose=0)
        y_scaler = prep.get("y_scaler")
        if y_scaler is not None:
            raw = float(y_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1))[0, 0])
        else:
            raw = float(y_pred_scaled.reshape(-1)[0])
    except Exception as exc:
        logger.warning("Keras inference error: %s", exc)
        return None

    # PV model output is Watts → convert to kW; consumption is already kW
    if target == "production":
        raw = raw / 1000.0

    return round(max(0.0, raw), 4)


# =========================================================================== #
# Scikit-learn (sklearn) inference                                              #
# =========================================================================== #

def _features_for_sklearn(model: ImportedModel, context: dict) -> list[list[float]]:
    feature_names = model.input_schema.get("features") or [
        "hour", "recent_production_kw", "recent_consumption_kw",
        "battery_soc", "pv_nominal_power_kw",
    ]
    return [[float(context.get(name, 0.0) or 0.0) for name in feature_names]]


def _pv_static_features(house, feature_cols: list[str]) -> dict[str, float]:
    """
    Last known value for every non-weather PV feature column, fetched once
    per forecast request (not once per horizon — these don't change across a
    single predict_future() call, so re-querying per step was pure overhead:
    with 144 steps/day it meant >1000 redundant DB round-trips for values
    that were always going to be the same "most recent measurement").
    """
    static: dict[str, float] = {}
    for col in feature_cols:
        mtype = PV_FEATURE_MAP.get(col)
        if mtype is None or mtype in PV_WEATHER_MEASUREMENT_TYPES:
            continue
        values = _fetch_recent_measurements(house, mtype, 1)
        if not values:
            continue
        val = values[-1]
        if col == "Pmpp":
            val = val * 1000.0
        static[col] = float(val)
    return static


def _build_pv_features_flat(
    feature_cols: list[str], weather_row: dict | None, static_values: dict[str, float]
) -> np.ndarray:
    """
    Single-row feature vector for the production Random Forest — same
    PV_FEATURE_MAP / weather-override logic as _build_pv_sequence, but no
    sequence dimension: the RF was trained on one timestep at a time, so each
    horizon's prediction depends only on that horizon's own forecasted
    weather + last known panel electricals, never on a stale shared window.
    """
    row: list[float] = []
    for col in feature_cols:
        mtype = PV_FEATURE_MAP.get(col)
        if mtype is None:
            row.append(np.nan)
            continue
        if mtype in PV_WEATHER_MEASUREMENT_TYPES and weather_row and weather_row.get(mtype) is not None:
            row.append(float(weather_row[mtype]))
            continue
        row.append(static_values.get(col, np.nan))
    return np.array(row, dtype=float).reshape(1, -1)


def _predict_pv_sklearn(
    model_record: ImportedModel,
    house,
    weather_row: dict | None,
    static_values: dict[str, float] | None,
) -> float | None:
    artifact = _get_sklearn_artifact_cached(model_record)
    if artifact is None:
        return None
    try:
        pipeline = artifact.get("pipeline", artifact) if isinstance(artifact, dict) else artifact
        feature_cols = model_record.feature_columns or (
            artifact.get("feature_columns", []) if isinstance(artifact, dict) else []
        )
        if not feature_cols:
            return None
        if static_values is None:
            static_values = _pv_static_features(house, feature_cols)
        X = _build_pv_features_flat(feature_cols, weather_row, static_values)
        raw = float(pipeline.predict(X)[0])
        return round(max(0.0, raw / 1000.0), 4)  # Watts -> kW
    except Exception as exc:
        logger.warning("sklearn PV inference error: %s", exc)
        return None


def _forecast_production_sklearn_batch(
    model_record: ImportedModel,
    house,
    now: datetime,
    n_steps: int,
    step_minutes: int,
    weather_lookup: dict[datetime, dict],
) -> list[dict] | None:
    """
    Batched RF inference for the whole requested horizon in a single
    pipeline.predict() call. A lone RandomForest (n_estimators=200,
    n_jobs=-1) predicting one row at a time pays joblib's parallel-backend
    dispatch overhead (~50-60ms) on every call regardless of how trivial the
    actual computation is — that overhead barely grows when batched, so
    144 rows at once is close to as fast as 1.
    """
    artifact = _get_sklearn_artifact_cached(model_record)
    if artifact is None:
        return None
    pipeline = artifact.get("pipeline", artifact) if isinstance(artifact, dict) else artifact
    feature_cols = model_record.feature_columns or (
        artifact.get("feature_columns", []) if isinstance(artifact, dict) else []
    )
    if not feature_cols:
        return None

    static_values = _pv_static_features(house, feature_cols)
    horizons = [now + timedelta(minutes=step_minutes * step) for step in range(1, n_steps + 1)]
    weather_rows = [_weather_row_for_horizon(weather_lookup, h) for h in horizons]
    X = np.vstack([_build_pv_features_flat(feature_cols, wr, static_values) for wr in weather_rows])

    try:
        raw_preds = pipeline.predict(X)
    except Exception as exc:
        logger.warning("sklearn PV batch inference error: %s", exc)
        return None

    results = []
    for step, (horizon, weather_row, raw) in enumerate(zip(horizons, weather_rows, raw_preds), start=1):
        value = round(max(0.0, float(raw) / 1000.0), 4)
        value = _apply_production_night_zero("production", horizon, weather_row, value)
        results.append({
            "horizon": horizon,
            "horizon_minutes": step_minutes * step,
            "forecast_value": value,
            "value": value,
            "model": model_record,
            "input_snapshot": {"mode": "sklearn", "weather": weather_row or {}},
        })
    return results


def _predict_with_sklearn_model(
    model: ImportedModel,
    context: dict,
    house=None,
    weather_row: dict | None = None,
    static_values: dict[str, float] | None = None,
) -> float | None:
    if model.target == "production":
        return _predict_pv_sklearn(model, house, weather_row, static_values)
    artifact = _get_sklearn_artifact_cached(model)
    if artifact is None:
        return None
    try:
        estimator = artifact.get("pipeline", artifact) if isinstance(artifact, dict) else artifact
        raw = estimator.predict(_features_for_sklearn(model, context))[0]
        return round(max(float(raw), 0.0), 3)
    except Exception as exc:
        logger.warning("sklearn inference error: %s", exc)
        return None


# =========================================================================== #
# Main forecasting entry points                                                 #
# =========================================================================== #

def forecast_value(
    target: str,
    horizon,
    house=None,
    weather_row: dict | None = None,
    static_values: dict[str, float] | None = None,
) -> tuple[float, ImportedModel, dict]:
    """
    Return (predicted_kw, model_record, metadata_snapshot) for a single horizon.

    Priority: Keras model → sklearn model → profile fallback. Used directly
    for production (single-shot per horizon, no historical rollout needed)
    and as a per-step fallback for consumption when the GRU rollout can't run.

    `static_values` (sklearn/production only) are the non-weather feature
    values shared by every horizon in this request — pass them in once from
    predict_future() to avoid re-querying the DB per step.
    """
    context = _feature_context(house, horizon)

    keras_record = _active_keras_model(target)
    if keras_record is not None:
        value = _predict_with_keras_model(keras_record, house, horizon, target, weather_row=weather_row)
        if value is not None:
            value = _apply_production_night_zero(target, horizon, weather_row, value)
            return value, keras_record, {
                "mode": keras_record.model_type,
                "horizon_hour": horizon.hour,
                "features": context,
                "weather": weather_row or {},
            }

    sklearn_record = _active_sklearn_model(target)
    if sklearn_record is not None:
        value = _predict_with_sklearn_model(
            sklearn_record, context, house=house, weather_row=weather_row, static_values=static_values
        )
        if value is not None:
            value = _apply_production_night_zero(target, horizon, weather_row, value)
            return value, sklearn_record, {"mode": "sklearn", "features": context, "weather": weather_row or {}}

    profile_model = get_or_create_profile_model(target)
    capacity = context["pv_nominal_power_kw"]
    if target == "production":
        profile = _solar_profile(horizon.hour, capacity)
        value = (profile * 0.75) + (context["recent_production_kw"] * 0.25)
    else:
        value = _consumption_profile(horizon.hour, context["recent_consumption_kw"])
    return round(max(0.0, value), 3), profile_model, {"mode": "profile_fallback", "features": context}


def forecast_grid(hours: int, step_minutes: int) -> tuple[int, int, int, datetime]:
    """
    Shared (n_steps, hours, step_minutes, now) computation, so callers that
    need to know the exact horizon set predict_future() will use — e.g. to
    check whether a fresh forecast already covers it — stay in sync with it.
    """
    hours = max(1, min(int(hours), 168))
    step_minutes = max(1, min(int(step_minutes), 120))
    n_steps = max(1, min(round(hours * 60 / step_minutes), MAX_STEPS))
    now = timezone.now().replace(second=0, microsecond=0)
    now = now - timedelta(minutes=now.minute % step_minutes)
    return n_steps, hours, step_minutes, now


def forecast_horizons(hours: int, step_minutes: int) -> list[datetime]:
    n_steps, _hours, step_minutes, now = forecast_grid(hours, step_minutes)
    return [now + timedelta(minutes=step_minutes * i) for i in range(1, n_steps + 1)]


def predict_future(
    target: str, house=None, hours: int = 24, step_minutes: int = DEFAULT_STEP_MINUTES
) -> list[dict]:
    n_steps, hours, step_minutes, now = forecast_grid(hours, step_minutes)

    if target == "consumption":
        keras_record = _active_keras_model(target)
        if keras_record is not None:
            points = _rollout_consumption_gru(keras_record, house, now, n_steps, step_minutes)
            if points is not None:
                return points
        # Rollout unavailable (no active GRU / preprocessing failed to load):
        # fall through to the generic per-step loop below.

    # Fetch the weather forecast once for the whole window (only production needs it).
    weather_lookup = _weather_forecast_lookup(house, hours) if target == "production" else {}

    if target == "production":
        sklearn_record = _active_sklearn_model(target)
        if sklearn_record is not None:
            points = _forecast_production_sklearn_batch(
                sklearn_record, house, now, n_steps, step_minutes, weather_lookup
            )
            if points is not None:
                return points
        # Batch path unavailable: fall through to the generic per-step loop
        # below (Keras PV fallback, or profile).

    points = []
    for step in range(1, n_steps + 1):
        horizon = now + timedelta(minutes=step_minutes * step)
        weather_row = (
            _weather_row_for_horizon(weather_lookup, horizon) if target == "production" else None
        )
        value, model, snapshot = forecast_value(target, horizon, house=house, weather_row=weather_row)
        points.append({
            "horizon": horizon,
            "horizon_minutes": step_minutes * step,
            "forecast_value": value,
            "value": value,
            "model": model,
            "input_snapshot": snapshot,
        })
    return points


# A full 24h/10-min consumption forecast is a 144-step *sequential*
# autoregressive rollout (~15s even with the model cached — the cost is the
# inference calls themselves, not loading), so paginating through it must not
# recompute the whole thing on every page turn. If a complete, recent-enough
# set of Forecast rows already covers the requested window, reuse it.
FORECAST_FRESHNESS_SECONDS = 90


def fresh_forecast_queryset(target: str, house, horizons: list[datetime]):
    """
    Return the persisted Forecast queryset for `horizons` if it's complete
    and was generated within FORECAST_FRESHNESS_SECONDS, else None.
    """
    if not horizons:
        return None
    qs = Forecast.objects.filter(target=target, horizon__in=horizons)
    qs = qs.filter(house=house) if house is not None else qs.filter(house__isnull=True)
    rows = list(qs.values_list("horizon", "created_at"))
    if len(rows) != len(horizons):
        return None
    cutoff = timezone.now() - timedelta(seconds=FORECAST_FRESHNESS_SECONDS)
    if any(created_at < cutoff for _horizon, created_at in rows):
        return None
    return qs


def persist_forecasts(target: str, points: list[dict], house=None) -> ImportedModel:
    horizons = [p["horizon"] for p in points]
    existing = Forecast.objects.filter(target=target, horizon__in=horizons)
    existing = existing.filter(house=house) if house is not None else existing.filter(house__isnull=True)
    existing.delete()

    Forecast.objects.bulk_create([
        Forecast(
            house=house,
            model=p.get("model"),
            target=target,
            horizon=p["horizon"],
            horizon_minutes=p["horizon_minutes"],
            forecast_value=p["forecast_value"],
            input_snapshot=p.get("input_snapshot", {}),
        )
        for p in points
    ])
    return points[0]["model"] if points else get_or_create_profile_model(target)


def persist_predictions(target: str, points: list[dict], house=None) -> ImportedModel:
    return persist_forecasts(target, points, house=house)


def seed_forecasts_for_house(house, hours: int = 24, replace: bool = False) -> None:
    for target in sorted(VALID_TARGETS):
        qs = Forecast.objects.filter(house=house, target=target, horizon__gte=timezone.now())
        if qs.exists() and not replace:
            continue
        if replace:
            qs.delete()
        points = predict_future(target, house=house, hours=hours)
        persist_forecasts(target, points, house=house)


def seed_predictions_for_house(house, hours: int = 24, replace: bool = False) -> None:
    seed_forecasts_for_house(house, hours=hours, replace=replace)
