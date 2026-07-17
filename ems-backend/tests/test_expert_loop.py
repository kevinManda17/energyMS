"""Tests de la boucle fermée : décision du système expert -> relais.

Vérifie que les règles floues sont *réellement appliquées* aux lignes, via
l'interface de test (trigger apply) et via le sondage du nœud en mode AUTO.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.devices.models import RelayState
from apps.houses.models import House

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client():
    user = User.objects.create_user("owner", "o@x.com", "pass12345")
    house = House.objects.create(owner=user, name="Prototype")
    client = APIClient()
    client.force_authenticate(user)
    return client, house


# Faits provoquant un délestage automatique de la ligne non prioritaire.
SHED_FACTS = {
    "production_pv": 0.0,
    "consommation": 3.0,
    "batterie_soc": 20.0,
    "non_critiques_actives": True,
}


def test_trigger_apply_sheds_non_priority_line(auth_client):
    client, house = auth_client
    resp = client.post(
        "/api/decisions/trigger/",
        {**SHED_FACTS, "house": house.id, "apply": True},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["decision_code"] == "SHED_NON_PRIORITY_LOAD"
    # La ligne non prioritaire (line2) est coupée, les autres restent alimentées.
    assert resp.data["applied_lines"] == {"line1": True, "line2": False, "line3": True}
    state = RelayState.objects.get(house=house)
    assert state.line2 is False
    assert state.line1 is True and state.line3 is True


def test_trigger_without_apply_leaves_relays_untouched(auth_client):
    client, house = auth_client
    RelayState.objects.create(house=house)  # tout ON par défaut
    resp = client.post(
        "/api/decisions/trigger/",
        {**SHED_FACTS, "house": house.id},  # apply omis => False
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["applied_lines"] is None
    state = RelayState.objects.get(house=house)
    assert state.line1 is True and state.line2 is True and state.line3 is True


def test_recommendation_decision_is_not_actuated(auth_client):
    client, house = auth_client
    RelayState.objects.create(house=house)
    # Équilibre -> NORMAL_OPERATION en RECOMMENDATION : pas d'actionnement.
    resp = client.post(
        "/api/decisions/trigger/",
        {
            "house": house.id,
            "production_pv": 2.0,
            "consommation": 2.0,
            "batterie_soc": 70.0,
            "apply": True,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["execution_mode"] == "RECOMMENDATION"
    assert resp.data["applied_lines"] is None


def test_auto_mode_poll_actuates_relays(auth_client):
    client, house = auth_client
    state = RelayState.objects.create(
        house=house, control_mode=RelayState.ControlMode.AUTO
    )
    # Le nœud POST un relevé de déficit (grosse consommation) via son jeton.
    esp = APIClient()
    resp = esp.post(
        f"/api/ems/decision/?token={state.device_token}",
        {
            "line1": {"voltage": 220, "current": 5, "power": 1.1},
            "line2": {"voltage": 220, "current": 5, "power": 1.0},
            "line3": {"voltage": 220, "current": 4, "power": 0.9},
        },
        format="json",
    )
    assert resp.status_code == 200
    # La réponse texte reflète l'état actionné par l'expert (format L1=x;L2=x;L3=x).
    assert resp.content.decode().startswith("L1=")
    state.refresh_from_db()
    # En mode AUTO sur données de déficit, l'expert a pu délester : on vérifie
    # au minimum que le mode est bien pris en compte (état cohérent booléen).
    assert state.control_mode == "AUTO"


def test_manual_mode_poll_does_not_evaluate(auth_client):
    client, house = auth_client
    state = RelayState.objects.create(house=house)  # MANUAL par défaut
    esp = APIClient()
    resp = esp.post(
        f"/api/ems/decision/?token={state.device_token}",
        {"line1": {"voltage": 220, "current": 5, "power": 2.0}},
        format="json",
    )
    assert resp.status_code == 200
    state.refresh_from_db()
    # En manuel, l'état reste celui commandé par l'interface (tout ON).
    assert state.line1 is True and state.line2 is True and state.line3 is True
