"""
Forecasting service for EMS inference.

Supports three inference backends:
  1. Keras sequence models (GRU, LSTM, CNN-LSTM, LSTM-Attention)
     with separate preprocessing.joblib (imputer + scalers).
  2. Scikit-learn pipelines stored as .joblib.
  3. Hourly profile fallback (mathematical solar/consumption model).

Keras inference flow:
  - Fetch the last `sequence_length` Measurement records from the DB.
  - Map EMS measurement_type → model feature column.
  - Fill missing features with medians from preprocessing.joblib.
  - Scale → build 3-D sequence → model.predict() → inverse-scale.
  - For each forecast horizon, override temporal features (hour, dayofweek, …)
    so the model captures time-of-day patterns even without future sensor data.
"""
from __future__ import annotations

import logging
import math
import os
from datetime import timedelta

import joblib
import numpy as np
from django.utils import timezone

from apps.energy_assets.models import EnergyAsset
from apps.measurements.models import Measurement

from .models import Forecast, ImportedModel

logger = logging.getLogger("ems.forecasting")

VALID_TARGETS = {"production", "consumption"}
BASELINE_ALGORITHM = "HourlyProfileForecast"
PROFILE_MODEL_TYPE = "profile"
KERAS_MODEL_TYPES = {"keras_gru", "keras_lstm", "keras_cnn_lstm", "keras_lstm_att"}

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
CONSUMPTION_TEMPORAL = ["hour", "dayofweek", "month", "is_weekend"]

# --------------------------------------------------------------------------- #
# Feature mapping: EMS measurement_type → PV model feature column
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


# =========================================================================== #
# Keras inference                                                               #
# =========================================================================== #

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


def _fetch_recent_measurements(house, mtype: str, n: int) -> list[float]:
    """Return the last `n` values for a given measurement type, oldest first."""
    qs = (
        Measurement.objects.filter(house=house, measurement_type=mtype)
        .order_by("-timestamp")
        .values_list("value", flat=True)[:n]
    )
    return list(reversed(list(qs)))


def _build_consumption_sequence(house, prep: dict, horizon) -> np.ndarray | None:
    """
    Build a (1, sequence_length, n_features) array for the consumption GRU.

    If fewer than sequence_length measurements exist, the preprocessing median
    imputer will fill the missing values (same strategy as during training).
    """
    seq_len = prep.get("sequence_length", 36)
    feature_cols: list[str] = prep.get("feature_columns", [])
    if not feature_cols:
        return None

    # Gather raw values column by column
    rows: list[list[float | None]] = []
    for _ in range(seq_len):
        rows.append([None] * len(feature_cols))

    for col_idx, col in enumerate(feature_cols):
        if col in CONSUMPTION_TEMPORAL:
            continue
        mtype = CONSUMPTION_FEATURE_MAP.get(col)
        if mtype is None:
            continue
        values = _fetch_recent_measurements(house, mtype, seq_len)
        for row_offset, val in enumerate(values):
            actual_row = seq_len - len(values) + row_offset
            rows[actual_row][col_idx] = float(val)

    # Fill temporal features for each step using the target horizon
    # (we apply the horizon's temporal features to the whole sequence so the
    # model's temporal attention reflects the prediction time-of-day).
    tz_horizon = horizon
    for row_idx in range(seq_len):
        for col_idx, col in enumerate(feature_cols):
            if col == "hour":
                rows[row_idx][col_idx] = float(tz_horizon.hour)
            elif col == "dayofweek":
                rows[row_idx][col_idx] = float(tz_horizon.weekday())
            elif col == "month":
                rows[row_idx][col_idx] = float(tz_horizon.month)
            elif col == "is_weekend":
                rows[row_idx][col_idx] = float(1 if tz_horizon.weekday() >= 5 else 0)

    X = np.array(rows, dtype=float)  # (seq_len, n_features)

    imputer = prep.get("feature_imputer")
    x_scaler = prep.get("x_scaler")
    if imputer:
        X = imputer.transform(X)
    if x_scaler:
        X = x_scaler.transform(X)

    return X[np.newaxis, :, :]  # (1, seq_len, n_features)


def _build_pv_sequence(house, prep: dict, horizon) -> np.ndarray | None:
    """
    Build a (1, sequence_length, n_features) array for the PV LSTM.
    Features not available from DB are filled by the median imputer (same as training).
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
) -> float | None:
    """
    Run inference with a Keras sequence model.
    Returns the predicted value in kW, or None on any failure.
    """
    prep = _load_keras_preprocessing(model_record)
    if prep is None:
        return None

    keras_model = _load_keras_model(model_record)
    if keras_model is None:
        return None

    if target == "consumption":
        X = _build_consumption_sequence(house, prep, horizon)
    else:
        X = _build_pv_sequence(house, prep, horizon)

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


def _predict_with_sklearn_model(model: ImportedModel, context: dict) -> float | None:
    path = model.resolved_path
    if not path or path.startswith("internal://") or not os.path.exists(path):
        return None
    try:
        artifact = joblib.load(path)
        # Support both raw pipeline and wrapped dict (training convention)
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
) -> tuple[float, ImportedModel, dict]:
    """
    Return (predicted_kw, model_record, metadata_snapshot) for a single horizon.

    Priority: Keras model → sklearn model → profile fallback.
    """
    context = _feature_context(house, horizon)

    # 1. Try active Keras model
    keras_record = _active_keras_model(target)
    if keras_record is not None:
        value = _predict_with_keras_model(keras_record, house, horizon, target)
        if value is not None:
            # PV at night: if irradiance from recent weather is 0, override to 0
            if target == "production":
                irr = _recent_average(house, "irradiance", fallback=-1)
                if irr == 0 or (irr < 0 and not (5 <= horizon.hour <= 19)):
                    value = 0.0
            return value, keras_record, {
                "mode": keras_record.model_type,
                "horizon_hour": horizon.hour,
                "features": context,
            }

    # 2. Try active sklearn model
    sklearn_record = _active_sklearn_model(target)
    if sklearn_record is not None:
        value = _predict_with_sklearn_model(sklearn_record, context)
        if value is not None:
            return value, sklearn_record, {"mode": "sklearn", "features": context}

    # 3. Profile fallback
    profile_model = get_or_create_profile_model(target)
    capacity = context["pv_nominal_power_kw"]
    if target == "production":
        profile = _solar_profile(horizon.hour, capacity)
        value = (profile * 0.75) + (context["recent_production_kw"] * 0.25)
    else:
        value = _consumption_profile(horizon.hour, context["recent_consumption_kw"])
    return round(max(0.0, value), 3), profile_model, {"mode": "profile_fallback", "features": context}


def predict_future(target: str, house=None, hours: int = 24) -> list[dict]:
    hours = max(1, min(int(hours), 168))
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    points = []
    for offset in range(1, hours + 1):
        horizon = now + timedelta(hours=offset)
        value, model, snapshot = forecast_value(target, horizon, house=house)
        points.append({
            "horizon": horizon,
            "horizon_minutes": offset * 60,
            "forecast_value": value,
            "value": value,
            "model": model,
            "input_snapshot": snapshot,
        })
    return points


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
