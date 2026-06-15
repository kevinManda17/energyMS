"""
Forecasting service: trains and applies Random Forest models for PV
production and energy consumption.

Features are simple time-based features (hour, day-of-week, month) plus a
lag value, which is enough for a credible baseline and keeps the module
fully self-contained when no real dataset is available.
"""
import math
from datetime import timedelta

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

MODELS_DIR = settings.ML_MODELS_DIR


def _time_features(timestamps: pd.Series) -> pd.DataFrame:
    ts = pd.to_datetime(timestamps)
    return pd.DataFrame(
        {
            "hour": ts.dt.hour,
            "dayofweek": ts.dt.dayofweek,
            "month": ts.dt.month,
            "hour_sin": np.sin(2 * np.pi * ts.dt.hour / 24),
            "hour_cos": np.cos(2 * np.pi * ts.dt.hour / 24),
        }
    )


def _synthetic_series(target: str, n_days: int = 30) -> pd.DataFrame:
    """Generate a plausible hourly series when no dataset is provided."""
    start = timezone.now() - timedelta(days=n_days)
    rows = []
    for i in range(n_days * 24):
        ts = start + timedelta(hours=i)
        hour = ts.hour
        if target == "production":
            # Bell-shaped solar curve peaking at noon.
            base = max(0.0, math.sin((hour - 6) / 12 * math.pi)) * 5.0
            value = max(0.0, base + np.random.normal(0, 0.4))
        else:
            # Two consumption peaks (morning + evening).
            morning = math.exp(-((hour - 8) ** 2) / 6)
            evening = math.exp(-((hour - 20) ** 2) / 6)
            value = 0.8 + 3.0 * (morning + evening) + np.random.normal(0, 0.3)
            value = max(0.1, value)
        rows.append({"timestamp": ts, target: round(value, 3)})
    return pd.DataFrame(rows)


def train_model(target: str, df: pd.DataFrame | None = None):
    """Train a RandomForest for the given target; returns (metrics, path)."""
    if df is None or target not in df.columns:
        df = _synthetic_series(target)

    X = _time_features(df["timestamp"])
    y = df[target].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = RandomForestRegressor(n_estimators=120, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(np.mean((y_test - preds) ** 2)))
    r2 = float(r2_score(y_test, preds))

    path = MODELS_DIR / f"rf_{target}.joblib"
    joblib.dump(model, path)

    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4),
            "n_samples": int(len(df))}, str(path)


def load_model(path: str):
    return joblib.load(path)


def predict_future(model, hours: int = 24):
    """Predict the next `hours` hourly values from now."""
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    horizons = [now + timedelta(hours=i + 1) for i in range(hours)]
    features = _time_features(pd.Series(horizons))
    values = model.predict(features)
    return [
        {"horizon": h, "value": round(float(max(0.0, v)), 3)}
        for h, v in zip(horizons, values)
    ]
