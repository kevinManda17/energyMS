"""Unités (W / kW / kWh) et séparation des températures ambiante / batterie."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.devices.models import RelayState
from apps.fuzzy_engine.engine import BATTERY_TEMP_DEFAULT_C, facts_from_house
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def house():
    user = User.objects.create_user("u_units", "u@x.com", "pass12345")
    return House.objects.create(owner=user, name="Proto")


# --------------------------------------------------------------------------- #
# Unités : le firmware envoie des WATTS, le backend stocke la conso en kW
# --------------------------------------------------------------------------- #

def test_esp32_watts_are_stored_as_kilowatts(house):
    """40 W envoyés par le nœud doivent donner 0,04 kW — pas 40 kW."""
    state = RelayState.objects.create(house=house)
    esp = APIClient()
    resp = esp.post(
        f"/api/ems/decision/?token={state.device_token}",
        {
            "line1": {"voltage": 220, "current": 0.045, "power": 10.0},
            "line2": {"voltage": 220, "current": 0.045, "power": 10.0},
            "line3": {"voltage": 220, "current": 0.09, "power": 20.0},
        },
        format="json",
    )
    assert resp.status_code == 200

    consumption = Measurement.objects.filter(
        house=house, measurement_type="consumption"
    ).first()
    assert consumption is not None
    assert consumption.unit == "kW"
    # 10 + 10 + 20 = 40 W  ->  0,04 kW
    assert consumption.value == pytest.approx(0.04, abs=1e-6)

    # La puissance brute reste disponible en W pour la traçabilité.
    power = Measurement.objects.filter(house=house, measurement_type="power").first()
    assert power is not None and power.unit == "W"
    assert power.value == pytest.approx(40.0, abs=1e-6)


def test_voltage_is_not_clamped_to_a_fixed_band(house):
    """Les fluctuations réelles doivent apparaître : aucune valeur forcée."""
    state = RelayState.objects.create(house=house)
    esp = APIClient()
    esp.post(
        f"/api/ems/decision/?token={state.device_token}",
        {
            "line1": {"voltage": 217.0, "current": 0.05, "power": 10.0},
            "line2": {"voltage": 210.0, "current": 0.05, "power": 10.0},
            "line3": {"voltage": 232.0, "current": 0.05, "power": 10.0},
        },
        format="json",
    )
    v = Measurement.objects.filter(house=house, measurement_type="voltage").first()
    # Moyenne réelle des 3 lignes = 219,67 V ; surtout pas ramenée à 224.
    assert v.value == pytest.approx((217.0 + 210.0 + 232.0) / 3, abs=1e-3)


def test_lines_without_mains_are_excluded_from_network_voltage(house):
    """Une ligne coupée (≈ 0 V) ne doit pas tirer la tension réseau vers le bas."""
    state = RelayState.objects.create(house=house)
    esp = APIClient()
    esp.post(
        f"/api/ems/decision/?token={state.device_token}",
        {
            "line1": {"voltage": 218.0, "current": 0.05, "power": 10.0},
            "line2": {"voltage": 0.0, "current": 0.0, "power": 0.0},
            "line3": {"voltage": 220.0, "current": 0.05, "power": 10.0},
        },
        format="json",
    )
    v = Measurement.objects.filter(house=house, measurement_type="voltage").first()
    assert v.value == pytest.approx(219.0, abs=1e-3)  # (218 + 220) / 2


# --------------------------------------------------------------------------- #
# Températures : ambiante (météo) != batterie (sonde)
# --------------------------------------------------------------------------- #

def test_weather_temperature_is_not_used_as_battery_temperature(house):
    """Une canicule à 38 °C ne doit pas être lue comme température batterie."""
    Measurement.objects.create(
        house=house, measurement_type="temperature", value=38.0, unit="°C",
        timestamp=timezone.now(),
    )
    facts = facts_from_house(house)
    assert facts.battery_temperature_c == BATTERY_TEMP_DEFAULT_C


def test_battery_probe_is_used_when_present(house):
    Measurement.objects.create(
        house=house, measurement_type="battery_temp", value=47.5, unit="°C",
        timestamp=timezone.now(),
    )
    facts = facts_from_house(house)
    assert facts.battery_temperature_c == pytest.approx(47.5)
