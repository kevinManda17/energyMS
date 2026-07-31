"""
Agrégats et décision par ligne — §2.6 de la refonte de la base.

Ce que ces tables rendent possible : un historique par ligne lisible, et un
raisonnement de délestage INTERROGEABLE — pas seulement consultable décision
par décision dans un champ JSON.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from apps.devices.models import Line
from apps.devices.provisioning import ensure_lines
from apps.houses.models import House
from apps.measurements.models import (
    ROLLUP_STEP_MINUTES,
    LineReading,
    LineRollup,
    MeasurementRollup,
    Quantity,
    floor_to_bucket,
    record,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def house():
    user = User.objects.create_user("rollups", "r@x.com", "pass12345")
    return House.objects.create(owner=user, name="Prototype")


# --------------------------------------------------------------------------- #
# Le pas de dix minutes
# --------------------------------------------------------------------------- #

def test_the_bucket_step_matches_the_training_resample():
    """Le pas n'est pas un réglage de confort.

    Il correspond au ré-échantillonnage du jeu de consommation sur lequel le
    GRU a été entraîné. La base produit donc directement le format attendu,
    au lieu d'obliger chaque usage à ré-échantillonner à la volée.
    """
    assert ROLLUP_STEP_MINUTES == 10


def test_an_instant_falls_into_its_own_ten_minute_bucket():
    instant = timezone.now().replace(hour=14, minute=37, second=42, microsecond=123)
    bucket = floor_to_bucket(instant)
    assert bucket.minute == 30
    assert bucket.second == 0 and bucket.microsecond == 0


# --------------------------------------------------------------------------- #
# Agrégats de grandeur
# --------------------------------------------------------------------------- #

def test_a_rollup_keeps_the_peak_not_only_the_mean(house):
    """Une moyenne seule efface les pointes — et ce sont elles qui délestent.

    Un intervalle dont la moyenne vaut 40 W et le maximum 900 W ne décrit pas
    la même maison qu'un intervalle plat à 40 W.
    """
    base = floor_to_bucket(timezone.now())
    for i, valeur in enumerate([20.0, 900.0, 20.0, 20.0]):
        record(house, Quantity.LOAD_POWER_W, valeur,
               base + timezone.timedelta(seconds=30 * i))

    call_command("build_rollups", "--house", str(house.id))

    agregat = MeasurementRollup.objects.get(
        house=house, quantity=Quantity.LOAD_POWER_W, bucket=base
    )
    assert agregat.sample_count == 4
    assert agregat.avg_value == pytest.approx(240.0)
    assert agregat.max_value == pytest.approx(900.0)
    assert agregat.min_value == pytest.approx(20.0)


def test_building_rollups_twice_does_not_duplicate(house):
    """Idempotente : un agrégat est un résumé, pas une vérité indépendante."""
    base = floor_to_bucket(timezone.now())
    record(house, Quantity.GRID_VOLTAGE_V, 219.0, base)

    call_command("build_rollups", "--house", str(house.id))
    call_command("build_rollups", "--house", str(house.id))

    assert MeasurementRollup.objects.filter(
        house=house, quantity=Quantity.GRID_VOLTAGE_V
    ).count() == 1


# --------------------------------------------------------------------------- #
# Agrégats de ligne
# --------------------------------------------------------------------------- #

def test_a_line_rollup_computes_energy_not_a_sum_of_powers(house):
    """ÉNERGIE = puissance x DURÉE.

    Sommer des puissances sans multiplier par le temps ne donne pas une
    énergie. C'est la confusion que docs/MEASUREMENTS_UNITS.md interdit depuis
    le début, et l'agrégat est le premier endroit du dépôt où le calcul est
    réellement fait.
    """
    ligne = ensure_lines(house)[0]
    base = floor_to_bucket(timezone.now())
    for i in range(4):
        LineReading.objects.create(
            line=ligne, timestamp=base + timezone.timedelta(seconds=30 * i),
            power_w=60.0, relay_closed=True, is_measured=True,
        )

    call_command("build_rollups", "--house", str(house.id))

    agregat = LineRollup.objects.get(line=ligne, bucket=base)
    assert agregat.avg_power_w == pytest.approx(60.0)
    # 60 W pendant 10 minutes = 10 Wh, et surtout PAS 240 (la somme).
    assert agregat.energy_wh == pytest.approx(60.0 * 10 / 60)


def test_an_unmeasured_reading_never_counts_as_zero_watts(house):
    """Une ligne muette n'est pas une ligne à 0 W.

    La compter pour zéro tirerait la moyenne vers le bas en inventant une
    information — exactement ce que la règle L006 du moteur interdit.
    """
    ligne = ensure_lines(house)[0]
    base = floor_to_bucket(timezone.now())
    LineReading.objects.create(line=ligne, timestamp=base, power_w=100.0,
                               relay_closed=True, is_measured=True)
    LineReading.objects.create(line=ligne,
                               timestamp=base + timezone.timedelta(seconds=30),
                               power_w=None, relay_closed=True, is_measured=False)

    call_command("build_rollups", "--house", str(house.id))

    agregat = LineRollup.objects.get(line=ligne, bucket=base)
    # 100 W et non 50 W : le relevé muet n'entre pas dans la moyenne.
    assert agregat.avg_power_w == pytest.approx(100.0)
    # Il compte en revanche dans l'échantillon : on sait qu'il a existé.
    assert agregat.sample_count == 2


def test_closed_ratio_measures_the_time_a_line_was_powered(house):
    """Ce qui permet de dire « la ligne 1 a été coupée 40 minutes hier ».

    Aucune donnée du système ne permettait de produire cette phrase.
    """
    ligne = ensure_lines(house)[0]
    base = floor_to_bucket(timezone.now())
    for i, ferme in enumerate([True, True, False, False]):
        LineReading.objects.create(
            line=ligne, timestamp=base + timezone.timedelta(seconds=30 * i),
            power_w=10.0 if ferme else 0.0, relay_closed=ferme, is_measured=True,
        )

    call_command("build_rollups", "--house", str(house.id))

    agregat = LineRollup.objects.get(line=ligne, bucket=base)
    assert agregat.closed_ratio == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# DecisionLine
# --------------------------------------------------------------------------- #

def _prototype_avec_releves(house):
    from apps.devices.models import RelayState

    call_command("seed_prototype", "--house", str(house.id))
    RelayState.objects.create(house=house)
    maintenant = timezone.now()
    for ligne, puissance in zip(ensure_lines(house), (12.1, 20.0, 11.0)):
        LineReading.objects.create(
            line=ligne, timestamp=maintenant, power_w=puissance,
            voltage_v=220.0, current_a=puissance / 220.0,
            relay_closed=True, is_measured=True,
        )
    for quantity, valeur in [
        (Quantity.PV_POWER_W, 0.0),
        (Quantity.LOAD_POWER_W, 3000.0),
        (Quantity.BATTERY_SOC_PCT, 22.0),
    ]:
        record(house, quantity, valeur, maintenant)


def test_a_decision_records_one_conclusion_per_line(house):
    """Le raisonnement par ligne devient INTERROGEABLE.

    Il vivait dans `Decision.reasoning_trace`, un JSON : consultable pour une
    décision qu'on regarde, inexploitable en masse. On ne pouvait pas demander
    « combien de fois la ligne 2 a-t-elle été protégée par un veto ? ».
    """
    from apps.fuzzy_engine.models import DecisionLine

    _prototype_avec_releves(house)
    client = _client_pour(house)
    resp = client.post("/api/decisions/trigger/",
                       {"house": house.id, "apply": True}, format="json")
    assert resp.status_code == 201

    conclusions = DecisionLine.objects.filter(decision__house=house)
    assert conclusions.count() == 3
    for conclusion in conclusions:
        assert conclusion.line_id is not None
        assert conclusion.state_before is not None
        assert conclusion.state_desired is not None


def test_was_applied_distinguishes_deciding_from_doing(house):
    """Décider n'est pas faire.

    En mode assisté la décision attend une validation humaine, en mode
    automatique la fenêtre de confirmation. Confondre les deux ferait croire à
    des coupures qui n'ont jamais eu lieu.
    """
    from apps.fuzzy_engine.models import DecisionLine

    _prototype_avec_releves(house)
    client = _client_pour(house)
    # `apply` omis : la decision est prise, rien n'est actionne.
    client.post("/api/decisions/trigger/", {"house": house.id}, format="json")

    conclusions = DecisionLine.objects.filter(decision__house=house)
    assert conclusions.exists()
    assert not conclusions.filter(was_applied=True).exists()


def test_a_veto_is_recorded_with_its_code(house):
    """Le code du véto se compte ; la phrase, elle, reste dans la trace."""
    from apps.devices.models import Equipment
    from apps.fuzzy_engine.models import DecisionLine

    _prototype_avec_releves(house)
    Equipment.objects.filter(house=house).update(priority="CRITICAL")

    client = _client_pour(house)
    client.post("/api/decisions/trigger/", {"house": house.id}, format="json")

    bloquees = DecisionLine.objects.filter(decision__house=house, is_blocked=True)
    assert bloquees.count() == 3
    # L003 : ligne portant une charge vitale.
    assert all(c.blocked_reason == "L003" for c in bloquees)
    assert all(c.shed_score == 0.0 for c in bloquees)


def _client_pour(house):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(house.owner)
    return client
