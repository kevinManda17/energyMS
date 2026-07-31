"""Unités (W / kW / kWh) et séparation des températures ambiante / batterie."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.devices.models import RelayState
from apps.fuzzy_engine.engine import facts_from_house
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

def test_esp32_watts_are_stored_as_watts(house):
    """40 W envoyés par le nœud restent 40 W — et il n'y a plus de doublon kW.

    L'invariant a CHANGE DE NATURE (§2.4). Le test verifiait que la conversion
    W -> kW etait bien appliquee ; il n'y a plus de conversion, donc plus
    d'occasion de se tromper. La puissance appelee est UNE grandeur, en watts,
    dont l'unite est portee par le nom (`load_power_w`). Le facteur 1000 de
    l'historique venait precisement de ce doublon : la meme puissance ecrite
    dans deux unites, ou il suffisait qu'un ecrivain se trompe de colonne.
    """
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

    from apps.measurements.models import Quantity

    puissance = Measurement.objects.filter(
        house=house, quantity=Quantity.LOAD_POWER_W
    ).first()
    assert puissance is not None
    # 10 + 10 + 20 = 40 W, et cela reste 40 W.
    assert puissance.value == pytest.approx(40.0, abs=1e-6)
    # L'unite est DEDUITE du nom, plus stockee : elle ne peut plus diverger.
    assert puissance.unit_symbol == "W"

    # Il n'existe plus de seconde ligne pour la meme puissance dans une autre
    # unite : c'est la disparition de ce doublon qui rend le bug impossible.
    assert Measurement.objects.filter(
        house=house, measurement_type="consumption"
    ).count() == 0


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
    from apps.measurements.models import Quantity
    v = Measurement.objects.filter(
        house=house, quantity=Quantity.GRID_VOLTAGE_V
    ).first()
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
    from apps.measurements.models import Quantity
    v = Measurement.objects.filter(
        house=house, quantity=Quantity.GRID_VOLTAGE_V
    ).first()
    assert v.value == pytest.approx(219.0, abs=1e-3)  # (218 + 220) / 2


# --------------------------------------------------------------------------- #
# Températures : ambiante (météo) != batterie (sonde)
# --------------------------------------------------------------------------- #

def test_weather_temperature_is_not_used_as_battery_temperature(house):
    """Une canicule à 38 °C ne doit pas être lue comme température batterie."""
    from apps.measurements.models import Quantity, Source, record
    record(house, Quantity.AMBIENT_TEMP_C, 38.0, timezone.now(),
           source=Source.WEATHER_API)
    facts = facts_from_house(house)
    # Sans sonde dediee, la temperature batterie est INCONNUE, pas « 25 C par
    # defaut ». La valeur neutre d'autrefois faisait affirmer a R015 que « la
    # temperature est normale », ce que le systeme n'avait aucun moyen de
    # savoir. Ce que ce test protege reste le meme : la meteo (38 C ici) ne
    # doit jamais servir de temperature batterie.
    assert facts.battery_temperature_c is None


def test_battery_probe_is_used_when_present(house):
    from apps.measurements.models import Quantity, record
    record(house, Quantity.BATTERY_TEMP_C, 47.5, timezone.now())
    facts = facts_from_house(house)
    assert facts.battery_temperature_c == pytest.approx(47.5)
