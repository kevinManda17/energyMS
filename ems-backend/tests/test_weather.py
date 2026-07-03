"""Weather collection endpoints + PV capacity scaling."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.energy_assets.models import EnergyAsset
from apps.forecasting.models import ImportedModel
from apps.forecasting.services import pv_capacity_estimate_kw, pv_scale_factor
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db

FAKE_SNAPSHOT = {
    "_timestamp": "2026-07-03T10:00",
    "irradiance": 640.0,
    "irradiance_tilt15": 700.0,
    "irradiance_tilt20": 710.0,
    "temperature": 27.5,
    "humidity": 55.0,
    "air_pressure": 1011.0,
    "wind_speed": 2.4,
    "wind_direction": 180.0,
}


@pytest.fixture
def weather_client(monkeypatch):
    monkeypatch.setattr(
        "apps.measurements.services.fetch_solar_snapshot",
        lambda lat, lon: dict(FAKE_SNAPSHOT),
    )
    user = User.objects.create_user("meteo", "meteo@x.com", "pass12345")
    house = House.objects.create(
        owner=user, name="Maison Meteo", latitude=-4.33, longitude=15.31
    )
    client = APIClient()
    client.force_authenticate(user)
    return client, house


def test_weather_collect_stores_measurements(weather_client):
    client, house = weather_client

    resp = client.post("/api/measurements/weather/collect/", {"house": house.id}, format="json")

    assert resp.status_code == 200
    result = resp.data["results"][0]
    assert result["house"] == house.id
    assert result["stored"] == len(FAKE_SNAPSHOT) - 1  # minus _timestamp
    assert result["values"]["irradiance"] == 640.0
    assert Measurement.objects.filter(house=house, measurement_type="irradiance").count() == 1


def test_weather_collect_is_idempotent_within_the_hour(weather_client):
    client, house = weather_client

    client.post("/api/measurements/weather/collect/", {"house": house.id}, format="json")
    client.post("/api/measurements/weather/collect/", {"house": house.id}, format="json")

    # Same Open-Meteo hourly timestamp → rows updated, never duplicated.
    assert Measurement.objects.filter(house=house, measurement_type="temperature").count() == 1


def test_weather_collect_defaults_to_all_accessible_houses(weather_client):
    client, house = weather_client
    other_owner = User.objects.create_user("autre", "autre@x.com", "pass12345")
    House.objects.create(owner=other_owner, name="Pas a moi")

    resp = client.post("/api/measurements/weather/collect/", {}, format="json")

    assert resp.status_code == 200
    assert [r["house"] for r in resp.data["results"]] == [house.id]


def test_weather_collect_rejects_foreign_house(weather_client):
    client, _house = weather_client
    other_owner = User.objects.create_user("autre2", "autre2@x.com", "pass12345")
    foreign = House.objects.create(owner=other_owner, name="Pas a moi")

    resp = client.post(
        "/api/measurements/weather/collect/", {"house": foreign.id}, format="json"
    )

    assert resp.status_code == 403


def test_weather_collect_reports_upstream_failure(weather_client, monkeypatch):
    client, house = weather_client
    monkeypatch.setattr(
        "apps.measurements.services.fetch_solar_snapshot", lambda lat, lon: None
    )

    resp = client.post("/api/measurements/weather/collect/", {"house": house.id}, format="json")

    assert resp.status_code == 502


def test_weather_status_reflects_last_collection(weather_client):
    client, house = weather_client

    resp = client.get(f"/api/measurements/weather/status/?house={house.id}")
    assert resp.status_code == 200
    assert resp.data["timestamp"] is None
    assert "auto_collect" in resp.data

    client.post("/api/measurements/weather/collect/", {"house": house.id}, format="json")
    resp = client.get(f"/api/measurements/weather/status/?house={house.id}")

    assert resp.data["timestamp"] is not None
    assert resp.data["values"]["temperature"] == 27.5
    assert resp.data["auto_collect"]["interval_minutes"] >= 5


# --------------------------------------------------------------------------- #
# PV capacity scaling                                                          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def scaling_house():
    user = User.objects.create_user("solaire", "sol@x.com", "pass12345")
    return House.objects.create(owner=user, name="Maison Solaire")


def _production_model(**extra):
    return ImportedModel.objects.create(
        name="Production PV", target="production", model_type="sklearn", **extra
    )


def test_pv_capacity_falls_back_to_house_estimate(scaling_house):
    assert pv_capacity_estimate_kw(scaling_house) is None

    scaling_house.pv_capacity_kw = 0.4
    scaling_house.save()
    assert pv_capacity_estimate_kw(scaling_house) == 0.4

    # An active PV panel asset with nominal power takes precedence.
    EnergyAsset.objects.create(
        house=scaling_house,
        name="Panneau",
        asset_type=EnergyAsset.AssetType.PV_PANEL,
        nominal_power_kw=0.3,
    )
    assert pv_capacity_estimate_kw(scaling_house) == 0.3


def test_pv_scale_factor_requires_both_reference_and_capacity(scaling_house):
    model = _production_model()
    assert pv_scale_factor(scaling_house, model) == (1.0, None)

    scaling_house.pv_capacity_kw = 0.4
    scaling_house.save()
    assert pv_scale_factor(scaling_house, model) == (1.0, 0.4)

    model.reference_peak_w = 250.0
    scale, capacity = pv_scale_factor(scaling_house, model)
    assert capacity == 0.4
    assert scale == pytest.approx(400.0 / 250.0)


def test_reference_peak_patch_is_admin_only(scaling_house):
    model = _production_model()
    client = APIClient()
    client.force_authenticate(scaling_house.owner)

    resp = client.patch(
        f"/api/forecasting/models/{model.id}/", {"reference_peak_w": 250.0}, format="json"
    )
    assert resp.status_code == 403

    admin = User.objects.create_user(
        "chef", "chef@x.com", "pass12345", role=User.Role.ADMIN
    )
    client.force_authenticate(admin)
    resp = client.patch(
        f"/api/forecasting/models/{model.id}/", {"reference_peak_w": 250.0}, format="json"
    )
    assert resp.status_code == 200
    model.refresh_from_db()
    assert model.reference_peak_w == 250.0
