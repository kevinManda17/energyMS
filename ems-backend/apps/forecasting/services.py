"""
Forecasting service for hourly EMS predictions.

This module answers the product question directly: what should production or
consumption look like in the next 1, 2, 24 hours, etc. It does not require the
end user to train a model from the platform.
"""
import math
from datetime import timedelta

from django.utils import timezone

from apps.measurements.models import Measurement

from .models import ForecastModel, Prediction

VALID_TARGETS = {"production", "consumption"}
BASELINE_ALGORITHM = "HourlyProfileForecast"


def get_or_create_forecast_model(target: str) -> ForecastModel:
    model = ForecastModel.objects.filter(
        target=target,
        algorithm=BASELINE_ALGORITHM,
        is_active=True,
    ).first()
    if model:
        return model
    return ForecastModel.objects.create(
        target=target,
        algorithm=BASELINE_ALGORITHM,
        file_path=f"internal://{BASELINE_ALGORITHM.lower()}/{target}",
        mae=None,
        rmse=None,
        r2=None,
        n_samples=0,
        is_active=True,
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


def _solar_profile(hour: int, pv_capacity_kw: float) -> float:
    daylight = max(0.0, math.sin((hour - 6) / 12 * math.pi))
    return max(0.0, daylight * pv_capacity_kw)


def _consumption_profile(hour: int, recent_avg_kw: float) -> float:
    morning = math.exp(-((hour - 7) ** 2) / 8)
    evening = math.exp(-((hour - 20) ** 2) / 8)
    daily_shape = 0.65 + 0.75 * morning + 1.05 * evening
    return max(0.15, recent_avg_kw * daily_shape)


def forecast_value(target: str, horizon, house=None) -> float:
    if target == "production":
        capacity = (house.pv_capacity_kw if house else 5.0) or 5.0
        recent = _recent_average(house, "production", fallback=capacity * 0.35)
        profile = _solar_profile(horizon.hour, capacity)
        value = (profile * 0.75) + (recent * 0.25)
        return round(max(0.0, value), 3)

    recent = _recent_average(house, "consumption", fallback=1.8)
    value = _consumption_profile(horizon.hour, recent)
    return round(max(0.0, value), 3)


def predict_future(target: str, house=None, hours: int = 24) -> list[dict]:
    hours = max(1, min(int(hours), 168))
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    points = []
    for offset in range(1, hours + 1):
        horizon = now + timedelta(hours=offset)
        points.append(
            {
                "horizon": horizon,
                "value": forecast_value(target, horizon, house=house),
            }
        )
    return points


def persist_predictions(target: str, points: list[dict], house=None) -> ForecastModel:
    model = get_or_create_forecast_model(target)
    horizons = [point["horizon"] for point in points]
    existing = Prediction.objects.filter(target=target, horizon__in=horizons)
    if house is None:
        existing = existing.filter(house__isnull=True)
    else:
        existing = existing.filter(house=house)
    existing.delete()

    Prediction.objects.bulk_create(
        [
            Prediction(
                house=house,
                model=model,
                target=target,
                horizon=point["horizon"],
                value=point["value"],
            )
            for point in points
        ]
    )
    return model


def seed_predictions_for_house(house, hours: int = 24, replace: bool = False) -> None:
    for target in sorted(VALID_TARGETS):
        qs = Prediction.objects.filter(
            house=house,
            target=target,
            horizon__gte=timezone.now(),
        )
        if qs.exists() and not replace:
            continue
        if replace:
            qs.delete()
        points = predict_future(target, house=house, hours=hours)
        persist_predictions(target, points, house=house)
