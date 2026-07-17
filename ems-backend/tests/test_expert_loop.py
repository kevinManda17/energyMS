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


DEFICIT_REPORT = {
    "line1": {"voltage": 220, "current": 5, "power": 1.1},
    "line2": {"voltage": 220, "current": 5, "power": 1.0},
    "line3": {"voltage": 220, "current": 4, "power": 0.9},
}


def _seed_deficit(house):
    """Mesures de déficit pour que l'expert veuille délester."""
    from apps.measurements.models import Measurement
    from django.utils import timezone
    now = timezone.now()
    for mt, val, unit in [("consumption", 3.0, "kW"), ("battery_soc", 18.0, "%"),
                          ("production", 0.0, "kW")]:
        Measurement.objects.create(house=house, measurement_type=mt, value=val,
                                   unit=unit, timestamp=now)


def test_auto_poll_waits_for_confirmation_window(auth_client):
    """Premier sondage en déficit : l'expert propose de délester mais NE coupe
    PAS tout de suite — il arme seulement la fenêtre de confirmation."""
    client, house = auth_client
    state = RelayState.objects.create(
        house=house, control_mode=RelayState.ControlMode.AUTO
    )
    _seed_deficit(house)
    esp = APIClient()
    resp = esp.post(f"/api/ems/decision/?token={state.device_token}",
                    DEFICIT_REPORT, format="json")
    assert resp.status_code == 200
    state.refresh_from_db()
    # Rien coupé, mais un candidat est en attente (L2 à couper).
    assert state.line1 is True and state.line2 is True and state.line3 is True
    assert state.auto_pending_lines == {"line1": True, "line2": False, "line3": True}
    assert state.auto_pending_since is not None


def test_auto_poll_applies_after_sustained_deficit(auth_client):
    """Quand le déficit persiste au-delà de la fenêtre, la coupure est appliquée."""
    from datetime import timedelta
    from django.utils import timezone

    client, house = auth_client
    state = RelayState.objects.create(
        house=house, control_mode=RelayState.ControlMode.AUTO
    )
    _seed_deficit(house)
    esp = APIClient()
    # 1er sondage : arme le candidat.
    esp.post(f"/api/ems/decision/?token={state.device_token}", DEFICIT_REPORT,
             format="json")
    # On antidate le candidat au-delà de la fenêtre de confirmation.
    state.refresh_from_db()
    state.auto_pending_since = timezone.now() - timedelta(seconds=10_000)
    state.last_measurement_at = None  # forcer le 're-due' du prochain sondage
    state.save(update_fields=["auto_pending_since", "last_measurement_at"])
    # 2e sondage : la condition est soutenue -> on applique.
    esp.post(f"/api/ems/decision/?token={state.device_token}", DEFICIT_REPORT,
             format="json")
    state.refresh_from_db()
    assert state.line2 is False  # ligne non prioritaire délestée
    assert state.line1 is True and state.line3 is True
    assert state.auto_pending_since is None  # candidat consommé


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
