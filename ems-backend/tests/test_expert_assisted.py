"""Mode ASSISTED (l'expert propose, l'humain valide) et mappage charge ↔ ligne."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.devices.models import Equipment, RelayState
from apps.fuzzy_engine.actuator import desired_lines_for_decision
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client():
    user = User.objects.create_user("owner2", "o2@x.com", "pass12345")
    house = House.objects.create(owner=user, name="Prototype")
    client = APIClient()
    client.force_authenticate(user)
    return client, house


DEFICIT_REPORT = {
    "line1": {"voltage": 220, "current": 5, "power": 1.1},
    "line2": {"voltage": 220, "current": 5, "power": 1.0},
    "line3": {"voltage": 220, "current": 4, "power": 0.9},
}


def _seed_deficit(house):
    from django.utils import timezone
    now = timezone.now()
    for mt, val, unit in [("consumption", 3.0, "kW"), ("battery_soc", 18.0, "%"),
                          ("production", 0.0, "kW")]:
        Measurement.objects.create(house=house, measurement_type=mt, value=val,
                                   unit=unit, timestamp=now)


# --------------------------------------------------------------------------- #
# Mappage charge <-> ligne
# --------------------------------------------------------------------------- #

class _Res:
    """Décision minimale pour tester le mapping."""
    def __init__(self, code, mode="AUTOMATIC"):
        self.decision_code = code
        self.execution_mode = mode


def test_shedding_targets_line_with_lowest_priority_equipment(auth_client):
    _client, house = auth_client
    # La ligne 3 porte la charge la moins prioritaire (contre-convention).
    Equipment.objects.create(house=house, name="Chauffe-eau", priority="NON_CRITICAL",
                             relay_line=3, status="ACTIVE")
    Equipment.objects.create(house=house, name="Frigo", priority="IMPORTANT",
                             relay_line=2, status="ACTIVE")
    desired = desired_lines_for_decision(_Res("SHED_NON_PRIORITY_LOAD"), house=house)
    # C'est bien L3 (charge non critique) qui est délestée, pas L2 par convention.
    assert desired == {"line1": True, "line2": True, "line3": False}


def test_low_priority_sheds_before_normal(auth_client):
    """LOW (Secondaire) doit se délester AVANT NORMAL — sinon LOW retombait,
    par défaut, au rang de NORMAL et n'était jamais choisie en premier."""
    _client, house = auth_client
    Equipment.objects.create(house=house, name="Ventilateur", priority="LOW",
                             relay_line=1, status="ACTIVE")
    Equipment.objects.create(house=house, name="Box internet", priority="NORMAL",
                             relay_line=2, status="ACTIVE")
    Equipment.objects.create(house=house, name="Frigo", priority="IMPORTANT",
                             relay_line=3, status="ACTIVE")
    desired = desired_lines_for_decision(_Res("SHED_NON_PRIORITY_LOAD"), house=house)
    # La ligne 1 (LOW) est délestée, pas la 2 (NORMAL) ni la 3 (IMPORTANT).
    assert desired == {"line1": False, "line2": True, "line3": True}


def test_critical_line_is_never_shed_automatically(auth_client):
    _client, house = auth_client
    # Toutes les lignes portent une charge critique : aucune coupure auto.
    for line in (1, 2, 3):
        Equipment.objects.create(house=house, name=f"Vital {line}",
                                 priority="CRITICAL", relay_line=line,
                                 status="ACTIVE")
    assert desired_lines_for_decision(_Res("SHED_NON_PRIORITY_LOAD"), house=house) is None


def test_fallback_convention_without_mapping(auth_client):
    """Sans équipement rattaché, on garde la convention firmware (L2 délestée)."""
    _client, house = auth_client
    desired = desired_lines_for_decision(_Res("SHED_NON_PRIORITY_LOAD"), house=house)
    assert desired == {"line1": True, "line2": False, "line3": True}


def test_protect_battery_keeps_critical_line(auth_client):
    _client, house = auth_client
    Equipment.objects.create(house=house, name="Respirateur", priority="CRITICAL",
                             relay_line=1, status="ACTIVE")
    desired = desired_lines_for_decision(_Res("PROTECT_BATTERY"), house=house)
    assert desired["line1"] is True  # la ligne critique reste alimentée


# --------------------------------------------------------------------------- #
# Mode ASSISTED
# --------------------------------------------------------------------------- #

def test_assisted_mode_proposes_without_cutting(auth_client):
    client, house = auth_client
    state = RelayState.objects.create(
        house=house, control_mode=RelayState.ControlMode.ASSISTED
    )
    _seed_deficit(house)
    esp = APIClient()
    esp.post(f"/api/ems/decision/?token={state.device_token}", DEFICIT_REPORT,
             format="json")
    state.refresh_from_db()
    # Proposition enregistrée, mais AUCUNE ligne coupée sans validation.
    assert state.auto_pending_lines == {"line1": True, "line2": False, "line3": True}
    assert state.line1 is True and state.line2 is True and state.line3 is True


def test_accepting_proposal_applies_it(auth_client):
    client, house = auth_client
    state = RelayState.objects.create(
        house=house, control_mode=RelayState.ControlMode.ASSISTED
    )
    _seed_deficit(house)
    esp = APIClient()
    esp.post(f"/api/ems/decision/?token={state.device_token}", DEFICIT_REPORT,
             format="json")

    resp = client.post(f"/api/houses/{house.id}/relays/", {"action": "accept"},
                       format="json")
    assert resp.status_code == 200
    state.refresh_from_db()
    assert state.line2 is False          # proposition appliquée
    assert state.auto_pending_lines is None  # proposition consommée


def test_dismissing_proposal_changes_nothing(auth_client):
    client, house = auth_client
    state = RelayState.objects.create(
        house=house, control_mode=RelayState.ControlMode.ASSISTED
    )
    _seed_deficit(house)
    esp = APIClient()
    esp.post(f"/api/ems/decision/?token={state.device_token}", DEFICIT_REPORT,
             format="json")

    resp = client.post(f"/api/houses/{house.id}/relays/", {"action": "dismiss"},
                       format="json")
    assert resp.status_code == 200
    state.refresh_from_db()
    assert state.line2 is True               # rien coupé
    assert state.auto_pending_lines is None  # proposition écartée


def test_proposal_endpoint_rejects_bad_action(auth_client):
    client, house = auth_client
    RelayState.objects.create(house=house)
    resp = client.post(f"/api/houses/{house.id}/relays/", {"action": "nope"},
                       format="json")
    assert resp.status_code == 400
