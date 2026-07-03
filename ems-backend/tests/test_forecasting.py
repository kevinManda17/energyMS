import joblib
import numpy as np
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

from apps.energy_assets.models import EnergyAsset
from apps.forecasting.models import Forecast, ImportedModel
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def forecast_client(monkeypatch):
    # No network in tests: the production path would otherwise call Open-Meteo.
    monkeypatch.setattr(
        "apps.forecasting.services.fetch_hourly_solar_forecast", lambda *a, **k: []
    )
    user = User.objects.create_user("forecast_user", "forecast@x.com", "pass12345")
    house = House.objects.create(
        owner=user,
        name="Residence Forecast",
    )
    EnergyAsset.objects.create(
        house=house,
        name="Panneaux PV",
        asset_type=EnergyAsset.AssetType.PV_PANEL,
        nominal_power_kw=4.5,
    )
    EnergyAsset.objects.create(
        house=house,
        name="Batterie",
        asset_type=EnergyAsset.AssetType.BATTERY,
        capacity_kwh=7.5,
    )
    now = timezone.now()
    for i in range(24):
        ts = now - timezone.timedelta(hours=i)
        Measurement.objects.create(
            house=house,
            measurement_type="production",
            value=2.0,
            unit="kW",
            timestamp=ts,
        )
        Measurement.objects.create(
            house=house,
            measurement_type="consumption",
            value=1.4,
            unit="kW",
            timestamp=ts,
        )

    client = APIClient()
    client.force_authenticate(user)
    return client, house


@pytest.fixture
def active_models(tmp_path):
    """
    Register one tiny (but real) sklearn model per target, exercising the same
    joblib-loading inference paths as the production RF — without the cost of
    loading the actual artifacts.
    """
    # Production: dict artifact {pipeline, feature_columns}, output in Watts.
    X_prod = np.array([[100.0, 25.0], [500.0, 30.0], [900.0, 28.0], [0.0, 22.0]])
    y_prod = np.array([120.0, 480.0, 850.0, 0.0])
    prod_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
        ("model", LinearRegression()),
    ]).fit(X_prod, y_prod)
    prod_path = tmp_path / "prod_model.joblib"
    joblib.dump(
        {"pipeline": prod_pipeline, "feature_columns": ["Pmpp", "air_temperature"]},
        prod_path,
    )
    prod = ImportedModel.objects.create(
        name="Production test",
        target="production",
        model_type="sklearn",
        file_path=str(prod_path),
        feature_columns=["Pmpp", "air_temperature"],
        input_schema={"features": ["Pmpp", "air_temperature"]},
        is_active=True,
    )

    # Consumption: bare pipeline over the generic context features (kW).
    rng = np.random.RandomState(0)
    X_cons = rng.rand(20, 5)
    y_cons = X_cons @ np.array([0.01, 0.1, 0.5, 0.001, 0.02]) + 0.8
    cons_pipeline = Pipeline([("model", LinearRegression())]).fit(X_cons, y_cons)
    cons_path = tmp_path / "cons_model.joblib"
    joblib.dump(cons_pipeline, cons_path)
    cons = ImportedModel.objects.create(
        name="Consommation test",
        target="consumption",
        model_type="sklearn",
        file_path=str(cons_path),
        input_schema={
            "features": [
                "hour",
                "recent_production_kw",
                "recent_consumption_kw",
                "battery_soc",
                "pv_nominal_power_kw",
            ]
        },
        is_active=True,
    )
    return prod, cons


def test_predict_returns_503_without_active_model(forecast_client):
    client, house = forecast_client

    resp = client.get(
        f"/api/forecasting/predict/?target=production&hours=1&house={house.id}"
    )

    assert resp.status_code == 503
    assert "Aucun modèle" in resp.data["detail"]
    assert Forecast.objects.filter(house=house).count() == 0


def test_predict_returns_and_stores_forecasts(forecast_client, active_models):
    client, house = forecast_client
    prod, _cons = active_models

    resp = client.get(
        f"/api/forecasting/predict/?target=production&hours=2&step_minutes=60&house={house.id}"
    )

    assert resp.status_code == 200
    assert resp.data["target"] == "production"
    assert resp.data["model"]["id"] == prod.id
    assert len(resp.data["predictions"]) == 2
    assert Forecast.objects.filter(house=house, target="production").count() == 2
    assert all(point["value"] >= 0 for point in resp.data["predictions"])


def test_predict_supports_consumption_target(forecast_client, active_models):
    client, house = forecast_client

    resp = client.get(
        f"/api/forecasting/predict/?target=consumption&hours=3&step_minutes=60&house={house.id}"
    )

    assert resp.status_code == 200
    assert len(resp.data["predictions"]) == 3
    assert Forecast.objects.filter(house=house, target="consumption").count() == 3


def test_predict_defaults_to_10_minute_native_step(forecast_client, active_models):
    client, house = forecast_client

    resp = client.get(
        f"/api/forecasting/predict/?target=consumption&hours=1&house={house.id}"
    )

    assert resp.status_code == 200
    assert resp.data["step_minutes"] == 10
    # 1h of native 10-minute steps = 6 points, all fit on the default page.
    assert resp.data["pagination"]["count"] == 6
    assert len(resp.data["predictions"]) == 6
    assert Forecast.objects.filter(house=house, target="consumption").count() == 6


def test_predict_paginates_when_result_exceeds_page_size(forecast_client, active_models):
    client, house = forecast_client

    resp = client.get(
        "/api/forecasting/predict/"
        f"?target=production&hours=24&step_minutes=10&page_size=10&house={house.id}"
    )

    assert resp.status_code == 200
    pagination = resp.data["pagination"]
    assert pagination["count"] == 144
    assert pagination["page_size"] == 10
    assert pagination["num_pages"] == 15
    assert pagination["has_next"] is True
    assert pagination["has_previous"] is False
    assert len(resp.data["predictions"]) == 10
    # All 144 points are still persisted even though only page 1 is returned.
    assert Forecast.objects.filter(house=house, target="production").count() == 144

    resp_page2 = client.get(
        "/api/forecasting/predict/"
        f"?target=production&hours=24&step_minutes=10&page_size=10&page=2&house={house.id}"
    )
    assert resp_page2.data["pagination"]["has_previous"] is True
    first_horizon_page1 = resp.data["predictions"][0]["horizon"]
    first_horizon_page2 = resp_page2.data["predictions"][0]["horizon"]
    assert first_horizon_page2 > first_horizon_page1


def test_predict_rejects_foreign_house(forecast_client):
    client, _house = forecast_client
    other = User.objects.create_user("other", "other@x.com", "pass12345")
    foreign_house = House.objects.create(owner=other, name="Maison privee")

    resp = client.get(
        f"/api/forecasting/predict/?target=production&hours=1&house={foreign_house.id}"
    )

    assert resp.status_code == 403
