"""
Forecasting service for EMS inference.

The backend imports or references pre-trained models and runs inference over
fresh IoT measurements. When no active imported model is usable, EMS falls back
to a simple hourly profile forecast.
"""
import math
import os
from datetime import timedelta

import joblib
from django.utils import timezone

from apps.energy_assets.models import EnergyAsset
from apps.measurements.models import Measurement

from .models import Forecast, ImportedModel

VALID_TARGETS = {"production", "consumption"}
BASELINE_ALGORITHM = "HourlyProfileForecast"
PROFILE_MODEL_TYPE = "profile"


def get_or_create_profile_model(target: str) -> ImportedModel:
    model = ImportedModel.objects.filter(
        target=target,
        model_type=PROFILE_MODEL_TYPE,
        is_active=True,
    ).first()
    if model:
        return model
    return ImportedModel.objects.create(
        name=f"{BASELINE_ALGORITHM} {target}",
        target=target,
        model_type=PROFILE_MODEL_TYPE,
        file_path=f"internal://{BASELINE_ALGORITHM.lower()}/{target}",
        version="fallback",
        input_schema={
            "features": [
                "hour",
                "recent_production_kw",
                "recent_consumption_kw",
                "battery_soc",
                "pv_nominal_power_kw",
            ]
        },
        metrics={},
        is_active=True,
    )


def get_or_create_forecast_model(target: str) -> ImportedModel:
    return get_or_create_profile_model(target)


def _active_imported_model(target: str) -> ImportedModel | None:
    return (
        ImportedModel.objects.filter(target=target, is_active=True)
        .exclude(model_type=PROFILE_MODEL_TYPE)
        .order_by("-imported_at")
        .first()
    )


def _recent_average(house, measurement_type: str, fallback: float) -> float:
    if house is None:
        return fallback
    values = list(
        Measurement.objects.filter(house=house, measurement_type=measurement_type)
        .order_by("-timestamp")
        .values_list("value", flat=True)[:24]
    )
    if not values:
        return fallback
    return max(0.0, sum(float(v) for v in values) / len(values))


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
    capacity = sum(float(value or 0) for value in total)
    return capacity or fallback


def _solar_profile(hour: int, pv_capacity_kw: float) -> float:
    daylight = max(0.0, math.sin((hour - 6) / 12 * math.pi))
    return max(0.0, daylight * pv_capacity_kw)


def _consumption_profile(hour: int, recent_avg_kw: float) -> float:
    morning = math.exp(-((hour - 7) ** 2) / 8)
    evening = math.exp(-((hour - 20) ** 2) / 8)
    daily_shape = 0.65 + 0.75 * morning + 1.05 * evening
    return max(0.15, recent_avg_kw * daily_shape)


def _feature_context(house, horizon) -> dict:
    capacity = pv_nominal_power_kw(house)
    return {
        "hour": horizon.hour,
        "weekday": horizon.weekday(),
        "recent_production_kw": _recent_average(
            house, "production", fallback=capacity * 0.35
        ),
        "recent_consumption_kw": _recent_average(house, "consumption", fallback=1.8),
        "battery_soc": _recent_average(house, "battery_soc", fallback=50.0),
        "pv_nominal_power_kw": capacity,
    }


def _features_for_model(model: ImportedModel, context: dict) -> list[list[float]]:
    feature_names = model.input_schema.get("features") or [
        "hour",
        "recent_production_kw",
        "recent_consumption_kw",
        "battery_soc",
        "pv_nominal_power_kw",
    ]
    return [[float(context.get(name, 0.0) or 0.0) for name in feature_names]]


def _predict_with_imported_model(model: ImportedModel, context: dict) -> float | None:
    path = model.resolved_path
    if not path or path.startswith("internal://") or not os.path.exists(path):
        return None
    try:
        estimator = joblib.load(path)
        raw = estimator.predict(_features_for_model(model, context))[0]
        return round(max(float(raw), 0.0), 3)
    except Exception:
        return None


def forecast_value(target: str, horizon, house=None) -> tuple[float, ImportedModel, dict]:
    context = _feature_context(house, horizon)
    imported_model = _active_imported_model(target)
    if imported_model is not None:
        imported_value = _predict_with_imported_model(imported_model, context)
        if imported_value is not None:
            return imported_value, imported_model, {
                "mode": "imported_model",
                "features": context,
            }

    profile_model = get_or_create_profile_model(target)
    if target == "production":
        profile = _solar_profile(horizon.hour, context["pv_nominal_power_kw"])
        value = (profile * 0.75) + (context["recent_production_kw"] * 0.25)
    else:
        value = _consumption_profile(horizon.hour, context["recent_consumption_kw"])
    return round(max(0.0, value), 3), profile_model, {
        "mode": "profile_fallback",
        "features": context,
    }


def predict_future(target: str, house=None, hours: int = 24) -> list[dict]:
    hours = max(1, min(int(hours), 168))
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    points = []
    for offset in range(1, hours + 1):
        horizon = now + timedelta(hours=offset)
        value, model, snapshot = forecast_value(target, horizon, house=house)
        points.append(
            {
                "horizon": horizon,
                "horizon_minutes": offset * 60,
                "forecast_value": value,
                "value": value,
                "model": model,
                "input_snapshot": snapshot,
            }
        )
    return points


def persist_forecasts(target: str, points: list[dict], house=None) -> ImportedModel:
    horizons = [point["horizon"] for point in points]
    existing = Forecast.objects.filter(target=target, horizon__in=horizons)
    existing = existing.filter(house=house) if house is not None else existing.filter(house__isnull=True)
    existing.delete()

    Forecast.objects.bulk_create(
        [
            Forecast(
                house=house,
                model=point.get("model"),
                target=target,
                horizon=point["horizon"],
                horizon_minutes=point["horizon_minutes"],
                forecast_value=point["forecast_value"],
                input_snapshot=point.get("input_snapshot", {}),
            )
            for point in points
        ]
    )
    return points[0]["model"] if points else get_or_create_profile_model(target)


def persist_predictions(target: str, points: list[dict], house=None) -> ImportedModel:
    return persist_forecasts(target, points, house=house)


def seed_forecasts_for_house(house, hours: int = 24, replace: bool = False) -> None:
    for target in sorted(VALID_TARGETS):
        qs = Forecast.objects.filter(
            house=house,
            target=target,
            horizon__gte=timezone.now(),
        )
        if qs.exists() and not replace:
            continue
        if replace:
            qs.delete()
        points = predict_future(target, house=house, hours=hours)
        persist_forecasts(target, points, house=house)


def seed_predictions_for_house(house, hours: int = 24, replace: bool = False) -> None:
    seed_forecasts_for_house(house, hours=hours, replace=replace)

