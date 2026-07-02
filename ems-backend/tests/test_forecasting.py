import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.energy_assets.models import EnergyAsset
from apps.forecasting.models import Forecast
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def forecast_client():
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


def test_predict_returns_and_stores_hourly_forecasts(forecast_client):
    client, house = forecast_client

    resp = client.get(
        f"/api/forecasting/predict/?target=production&hours=2&step_minutes=60&house={house.id}"
    )

    assert resp.status_code == 200
    assert resp.data["target"] == "production"
    assert resp.data["model"]["algorithm"] == "HourlyProfileForecast"
    assert len(resp.data["predictions"]) == 2
    assert Forecast.objects.filter(house=house, target="production").count() == 2
    assert all(point["value"] >= 0 for point in resp.data["predictions"])


def test_predict_supports_consumption_target(forecast_client):
    client, house = forecast_client

    resp = client.get(
        f"/api/forecasting/predict/?target=consumption&hours=3&step_minutes=60&house={house.id}"
    )

    assert resp.status_code == 200
    assert len(resp.data["predictions"]) == 3
    assert Forecast.objects.filter(house=house, target="consumption").count() == 3


def test_predict_defaults_to_10_minute_native_step(forecast_client):
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


def test_predict_paginates_when_result_exceeds_page_size(forecast_client):
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
