"""Tests de l'endpoint d'agrégations journalières /api/reports/summary/."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client():
    user = User.objects.create_user("alice", "a@x.com", "pass12345")
    house = House.objects.create(owner=user, name="Maison Rapport")
    client = APIClient()
    client.force_authenticate(user)
    return client, house


def _add_series(house, mtype, base, values, step_minutes=60):
    for i, v in enumerate(values):
        Measurement.objects.create(
            house=house,
            measurement_type=mtype,
            value=v,
            unit="kW",
            timestamp=base + timedelta(minutes=i * step_minutes),
        )


def test_summary_requires_auth():
    resp = APIClient().get("/api/reports/summary/")
    assert resp.status_code == 401


def test_summary_empty_returns_zeroed_days(auth_client):
    client, house = auth_client
    resp = client.get("/api/reports/summary/", {"house": house.id, "days": 7})
    assert resp.status_code == 200
    data = resp.data
    assert len(data["days"]) == 7
    assert data["totals"]["samples"] == 0
    assert data["totals"]["production_kwh"] == 0
    assert data["today"]["balance_kwh"] == 0


def test_summary_integrates_power_to_energy(auth_client):
    client, house = auth_client
    # 3 échantillons horaires à 2 kW constants → trapèze = 2 kW × 2 h = 4 kWh.
    base = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
    _add_series(house, "production", base, [2.0, 2.0, 2.0])
    # Consommation 1 kW constante sur les mêmes 2 heures → 2 kWh.
    _add_series(house, "consumption", base, [1.0, 1.0, 1.0])

    resp = client.get("/api/reports/summary/", {"house": house.id, "days": 1})
    assert resp.status_code == 200
    today = resp.data["today"]
    assert today["production_kwh"] == pytest.approx(4.0, abs=0.01)
    assert today["consumption_kwh"] == pytest.approx(2.0, abs=0.01)
    assert today["balance_kwh"] == pytest.approx(2.0, abs=0.01)
    assert resp.data["totals"]["samples"] == 6


def test_summary_ignores_large_gaps(auth_client):
    client, house = auth_client
    base = timezone.now().replace(hour=2, minute=0, second=0, microsecond=0)
    # Deux échantillons séparés de 8 h : le trou dépasse MAX_GAP_HOURS,
    # aucune énergie ne doit être fabriquée sur ce segment.
    Measurement.objects.create(
        house=house, measurement_type="production", value=5.0, unit="kW",
        timestamp=base,
    )
    Measurement.objects.create(
        house=house, measurement_type="production", value=5.0, unit="kW",
        timestamp=base + timedelta(hours=8),
    )
    resp = client.get("/api/reports/summary/", {"house": house.id, "days": 1})
    assert resp.data["today"]["production_kwh"] == 0


def test_summary_battery_average(auth_client):
    client, house = auth_client
    base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    _add_series(house, "battery_soc", base, [40.0, 60.0])
    resp = client.get("/api/reports/summary/", {"house": house.id, "days": 1})
    assert resp.data["today"]["battery_soc_avg"] == pytest.approx(50.0)


def test_summary_excludes_other_users_houses(auth_client):
    client, _house = auth_client
    other = User.objects.create_user("eve", "e@x.com", "pass12345")
    other_house = House.objects.create(owner=other, name="Maison Autre")
    Measurement.objects.create(
        house=other_house, measurement_type="production", value=9.0, unit="kW",
        timestamp=timezone.now(),
    )
    resp = client.get("/api/reports/summary/", {"house": other_house.id, "days": 1})
    assert resp.status_code == 200
    assert resp.data["houses"] == []
    assert resp.data["totals"]["samples"] == 0
