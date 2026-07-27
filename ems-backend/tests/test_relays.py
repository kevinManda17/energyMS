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
    # Le jeton d'appareil N'EST PLUS expose : c'est le secret partage qui
    # authentifie le noeud. Le renvoyer ici le faisait transiter a chaque
    # affichage de la page Equipements et atterrir dans le cache du
    # navigateur. Un secret qu'on affiche n'en est plus un.
    assert "device_token" not in resp.data


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


def test_ems_decision_without_a_token_is_refused(auth_client):
    """Sans jeton : 403. Il n'y a plus de mode « sans jeton ».

    Le repli « suivre le micro-reseau le plus recemment pilote » selectionnait
    un RelayState toutes maisons et tous utilisateurs confondus : quiconque
    pouvait atteindre le port 8000 recevait l'etat des relais du dernier
    micro-reseau actif — et le pilotait en lui renvoyant des mesures.
    """
    resp = APIClient().post("/api/ems/decision/", {}, format="json")
    assert resp.status_code == 403
    assert resp.content.decode() == "ERR=missing_token"


def test_a_node_cannot_reach_another_micro_grid(auth_client):
    """La propriete de securite, enoncee a l'endroit : un jeton ouvre UN
    micro-reseau, jamais celui du voisin."""
    client, house = auth_client
    house2 = House.objects.create(owner=house.owner, name="Prototype 2")
    client.get(f"/api/houses/{house.id}/relays/")
    client.get(f"/api/houses/{house2.id}/relays/")
    client.patch(f"/api/houses/{house2.id}/relays/", {"line3": False}, format="json")

    token1 = RelayState.objects.get(house=house).device_token
    esp = APIClient()
    resp = esp.post("/api/ems/decision/", {}, format="json",
                    HTTP_X_DEVICE_TOKEN=token1)
    # L'etat rendu est celui de SA maison, pas celui de la derniere pilotee.
    assert resp.content.decode() == "L1=1;L2=1;L3=1"


def test_an_invalid_token_is_refused(auth_client):
    resp = APIClient().post("/api/ems/decision/", {}, format="json",
                            HTTP_X_DEVICE_TOKEN="jeton-invente")
    assert resp.status_code == 403
    assert resp.content.decode() == "ERR=invalid_token"


def test_the_token_travels_in_a_header(auth_client):
    """L'en-tete plutot que l'URL : une URL finit dans les journaux Nginx,
    dans l'historique du navigateur et dans l'en-tete Referer."""
    client, house = auth_client
    client.get(f"/api/houses/{house.id}/relays/")
    token = RelayState.objects.get(house=house).device_token

    resp = APIClient().post("/api/ems/decision/", {}, format="json",
                            HTTP_X_DEVICE_TOKEN=token)
    assert resp.status_code == 200
    assert resp.content.decode() == "L1=1;L2=1;L3=1"


def test_the_url_parameter_still_works_for_deployed_nodes(auth_client):
    """Retrocompatibilite assumee : un noeud sur le terrain ne se reflashe pas
    a distance. Le parametre d'URL reste accepte, et signale comme obsolete."""
    client, house = auth_client
    client.get(f"/api/houses/{house.id}/relays/")
    token = RelayState.objects.get(house=house).device_token

    resp = APIClient().post(f"/api/ems/decision/?token={token}", {}, format="json")
    assert resp.status_code == 200


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


# --------------------------------------------------------------------------- #
# Charge utile enrichie : bloc continu de l'ESP32 secondaire
# --------------------------------------------------------------------------- #

ENRICHED_REPORT = {
    "line1": {"vSensorRms": 1.84, "iSensorRms": 0.05,
              "voltage": 220.0, "current": 0.055, "power": 12.1},
    "line2": {"vSensorRms": 1.86, "iSensorRms": 0.08,
              "voltage": 221.0, "current": 0.090, "power": 19.9},
    "line3": {"vSensorRms": 1.83, "iSensorRms": 0.05,
              "voltage": 219.0, "current": 0.050, "power": 11.0},
    "dc": {
        "batteryVoltage": 12.66, "batteryCurrent": 0.10, "batteryTemp": 27.5,
        "pvVoltage": 18.2, "pvCurrent": 1.4, "panelTemp": 44.0,
    },
}


def test_enriched_payload_feeds_the_three_sourceless_facts(auth_client):
    """Le bloc continu alimente enfin production, tension et courant batterie.

    Ces trois grandeurs n'avaient AUCUN producteur : le moteur retombait sur
    des valeurs par defaut, ce qui privait de fondement les onze regles qui en
    dependent.
    """
    client, house = auth_client
    client.get(f"/api/houses/{house.id}/relays/")
    token = RelayState.objects.get(house=house).device_token

    resp = APIClient().post("/api/ems/decision/", ENRICHED_REPORT,
                            format="json", HTTP_X_DEVICE_TOKEN=token)
    assert resp.status_code == 200

    stored = {
        m.measurement_type: m.value
        for m in Measurement.objects.filter(house=house)
    }
    assert stored["battery_voltage"] == pytest.approx(12.66)
    assert stored["battery_current"] == pytest.approx(0.10)
    assert stored["battery_temp"] == pytest.approx(27.5)
    # Puissances CALCULEES a partir des deux mesures conservees.
    assert stored["pv_power"] == pytest.approx(18.2 * 1.4, abs=1e-3)
    # Tolerance 1e-4 : les mesures sont stockees arrondies a 4 decimales.
    assert stored["production"] == pytest.approx(18.2 * 1.4 / 1000, abs=1e-4)


def test_enriched_payload_produces_a_battery_state(auth_client):
    """Le courant est quasi nul : la batterie est au repos, donc estimable
    par tension a vide."""
    from apps.energy_assets.models import BatteryState, EnergyAsset

    client, house = auth_client
    client.get(f"/api/houses/{house.id}/relays/")
    EnergyAsset.objects.create(
        house=house, name="Batterie 1",
        asset_type=EnergyAsset.AssetType.BATTERY, capacity_kwh=1.2, voltage=12.0,
    )
    token = RelayState.objects.get(house=house).device_token

    APIClient().post("/api/ems/decision/", ENRICHED_REPORT, format="json",
                     HTTP_X_DEVICE_TOKEN=token)

    state = BatteryState.objects.order_by("-timestamp").first()
    assert state is not None
    assert state.estimation_method == "OCV"
    assert state.soc_percent == pytest.approx(80.0, abs=2.0)
    assert state.direction == "IDLE"


def test_the_legacy_three_line_payload_still_works(auth_client):
    """Retrocompatibilite : un noeud deja pose sur le mur ne se met pas a jour
    a distance. La charge utile sans bloc `dc` doit continuer de passer."""
    client, house = auth_client
    client.get(f"/api/houses/{house.id}/relays/")
    token = RelayState.objects.get(house=house).device_token

    legacy = {k: v for k, v in ENRICHED_REPORT.items() if k != "dc"}
    resp = APIClient().post("/api/ems/decision/", legacy, format="json",
                            HTTP_X_DEVICE_TOKEN=token)
    assert resp.status_code == 200

    types = set(
        Measurement.objects.filter(house=house).values_list(
            "measurement_type", flat=True
        )
    )
    assert {"power", "consumption", "voltage", "current"} <= types
    # Aucune grandeur continue inventee faute de bloc `dc`.
    assert not types & {"battery_voltage", "battery_current", "pv_power"}
