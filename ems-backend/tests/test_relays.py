"""Tests du canal de commande des relais (interface -> backend -> noeud ESP32)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.devices.models import RelayState
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client():
    user = User.objects.create_user("owner", "o@x.com", "pass12345")
    house = House.objects.create(owner=user, name="Prototype")
    client = APIClient()
    client.force_authenticate(user)
    return client, house


def test_relays_get_creates_default_state_all_on(auth_client):
    client, house = auth_client
    resp = client.get(f"/api/houses/{house.id}/relays/")
    assert resp.status_code == 200
    assert resp.data["line1"] is True
    assert resp.data["line2"] is True
    assert resp.data["line3"] is True
    assert resp.data["device_token"]  # jeton généré


def test_relays_patch_updates_state(auth_client):
    client, house = auth_client
    client.get(f"/api/houses/{house.id}/relays/")  # crée l'état
    resp = client.patch(
        f"/api/houses/{house.id}/relays/", {"line2": False}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["line2"] is False
    assert resp.data["line1"] is True  # inchangé


def test_relays_isolation_between_users(auth_client):
    _client, _house = auth_client
    other = User.objects.create_user("eve", "e@x.com", "pass12345")
    other_house = House.objects.create(owner=other, name="Autre")
    resp = _client.get(f"/api/houses/{other_house.id}/relays/")
    assert resp.status_code in (403, 404)


def test_ems_decision_invalid_token():
    resp = APIClient().post(
        "/api/ems/decision/?token=nope", {}, format="json"
    )
    assert resp.status_code == 403


def test_ems_decision_returns_commanded_state(auth_client):
    client, house = auth_client
    # L'interface coupe la ligne 2.
    client.get(f"/api/houses/{house.id}/relays/")
    client.patch(f"/api/houses/{house.id}/relays/", {"line2": False}, format="json")
    token = RelayState.objects.get(house=house).device_token

    # Le noeud ESP32 (non authentifié, jeton dans l'URL) sonde le backend.
    esp = APIClient()
    resp = esp.post(
        f"/api/ems/decision/?token={token}",
        {"line1": {"voltage": 0, "current": 0, "power": 0}},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.content.decode() == "L1=1;L2=0;L3=1"

    # Le sondage a mémorisé le dernier contact et le relevé.
    state = RelayState.objects.get(house=house)
    assert state.last_contact_at is not None
    assert state.last_report == {"line1": {"voltage": 0, "current": 0, "power": 0}}


def test_ems_decision_no_token_before_any_command(auth_client):
    # Aucun ordre encore donné : le noeud sans jeton reçoit tout OFF (sécurité).
    resp = APIClient().post("/api/ems/decision/", {}, format="json")
    assert resp.status_code == 200
    assert resp.content.decode() == "L1=0;L2=0;L3=0"


def test_ems_decision_no_token_follows_last_commanded_house(auth_client):
    client, house = auth_client
    # Un second micro-réseau du même utilisateur, commandé en dernier.
    house2 = House.objects.create(owner=house.owner, name="Prototype 2")
    client.get(f"/api/houses/{house.id}/relays/")
    client.get(f"/api/houses/{house2.id}/relays/")
    # On coupe L3 sur house2 : il devient la cible automatique du noeud.
    client.patch(f"/api/houses/{house2.id}/relays/", {"line3": False}, format="json")

    resp = APIClient().post("/api/ems/decision/", {}, format="json")
    assert resp.content.decode() == "L1=1;L2=1;L3=0"

    # Piloter house ensuite bascule la cible du noeud vers house.
    client.patch(f"/api/houses/{house.id}/relays/", {"line1": False}, format="json")
    resp = APIClient().post("/api/ems/decision/", {}, format="json")
    assert resp.content.decode() == "L1=0;L2=1;L3=1"


def test_ems_decision_stores_real_measurements(auth_client):
    # Le relevé 3-lignes de l'ESP32 doit devenir des mesures réelles du
    # micro-réseau (ce qui alimente ensuite le moteur expert).
    client, house = auth_client
    client.get(f"/api/houses/{house.id}/relays/")
    token = RelayState.objects.get(house=house).device_token

    payload = {
        "line1": {"voltage": 220, "current": 0.5, "power": 110},
        "line2": {"voltage": 220, "current": 0.3, "power": 66},
        "line3": {"voltage": 218, "current": 0.2, "power": 44},
    }
    resp = APIClient().post(f"/api/ems/decision/?token={token}", payload, format="json")
    assert resp.status_code == 200

    # Le nœud envoie des WATTS (110+66+44 = 220 W) ; la consommation est
    # stockée en kW, donc 0,220 kW — et non 220 kW.
    cons = Measurement.objects.filter(house=house, measurement_type="consumption").first()
    assert cons is not None and cons.unit == "kW"
    assert cons.value == pytest.approx(0.220)
    power = Measurement.objects.filter(house=house, measurement_type="power").first()
    assert power is not None and power.unit == "W"
    assert power.value == pytest.approx(220.0)
    amp = Measurement.objects.filter(house=house, measurement_type="current").first()
    assert amp.value == pytest.approx(1.0)  # 0.5+0.3+0.2
    volt = Measurement.objects.filter(house=house, measurement_type="voltage").first()
    assert volt.value == pytest.approx((220 + 220 + 218) / 3)


def test_ems_decision_all_off(auth_client):
    client, house = auth_client
    client.get(f"/api/houses/{house.id}/relays/")
    client.patch(
        f"/api/houses/{house.id}/relays/",
        {"line1": False, "line2": False, "line3": False},
        format="json",
    )
    token = RelayState.objects.get(house=house).device_token
    resp = APIClient().post(f"/api/ems/decision/?token={token}", {}, format="json")
    assert resp.content.decode() == "L1=0;L2=0;L3=0"
