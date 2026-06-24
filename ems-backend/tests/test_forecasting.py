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
        f"/api/forecasting/predict/?target=production&hours=2&house={house.id}"
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
        f"/api/forecasting/predict/?target=consumption&hours=3&house={house.id}"
    )

    assert resp.status_code == 200
    assert len(resp.data["predictions"]) == 3
    assert Forecast.objects.filter(house=house, target="consumption").count() == 3


def test_predict_rejects_foreign_house(forecast_client):
    client, _house = forecast_client
    other = User.objects.create_user("other", "other@x.com", "pass12345")
    foreign_house = House.objects.create(owner=other, name="Maison privee")

    resp = client.get(
        f"/api/forecasting/predict/?target=production&hours=1&house={foreign_house.id}"
    )

    assert resp.status_code == 403
