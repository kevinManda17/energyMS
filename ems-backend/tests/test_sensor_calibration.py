"""Identité des capteurs, calibration par coefficient et détection de capteur suspect."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.devices import calibration
from apps.devices.models import Equipment, Sensor
from apps.houses.models import House

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client():
    user = User.objects.create_user("cal", "cal@x.com", "pass12345")
    house = House.objects.create(owner=user, name="Prototype")
    client = APIClient()
    client.force_authenticate(user)
    return client, house


def _voltage_sensor(house, code, line, factor=1.0, calibrated=False):
    from django.utils import timezone
    return Sensor.objects.create(
        house=house, code=code, name=code, sensor_type="voltage",
        line_number=line, unit="V", calibration_factor=factor,
        calibrated_at=timezone.now() if calibrated else None,
    )


# --------------------------------------------------------------------------- #
# Calcul du coefficient
# --------------------------------------------------------------------------- #

def test_propose_factor_from_multimeter_reading():
    # 1,84 V bruts lus, 219 V au multimètre -> coefficient ≈ 119,02
    factor = calibration.propose_factor(raw_value=1.84, reference_value=219.0)
    assert factor == pytest.approx(219.0 / 1.84)
    assert 1.84 * factor == pytest.approx(219.0)


def test_propose_factor_accounts_for_current_transformer_turns():
    """N tours du fil de phase font voir N × I au capteur."""
    # Charge réelle 0,045 A, mais 3 tours -> le capteur doit voir 0,135 A.
    factor = calibration.propose_factor(raw_value=0.09, reference_value=0.045, turns=3)
    assert factor == pytest.approx((0.045 * 3) / 0.09)


def test_propose_factor_rejects_zero_raw_value():
    with pytest.raises(ValueError):
        calibration.propose_factor(raw_value=0.0, reference_value=220.0)


# --------------------------------------------------------------------------- #
# Validation croisée : un capteur trop éloigné de ses semblables est suspect
# --------------------------------------------------------------------------- #

def test_similar_coefficients_are_all_considered_calibrated(auth_client):
    _client, house = auth_client
    for code, line, factor in [("V1", 1, 126.5), ("V2", 2, 129.2), ("V3", 3, 127.8)]:
        _voltage_sensor(house, code, line, factor, calibrated=True)

    counts = calibration.refresh_calibration_status(house)
    assert counts["suspect"] == 0
    assert counts["calibrated"] == 3
    assert all(s.calibration_status == "calibrated"
               for s in Sensor.objects.filter(house=house))


def test_outlier_coefficient_is_flagged_suspect(auth_client):
    _client, house = auth_client
    _voltage_sensor(house, "V1", 1, 126.5, calibrated=True)
    _voltage_sensor(house, "V2", 2, 129.2, calibrated=True)
    _voltage_sensor(house, "V3", 3, 300.0, calibrated=True)  # montage douteux

    calibration.refresh_calibration_status(house)
    assert Sensor.objects.get(house=house, code="V3").calibration_status == "suspect"
    # Les capteurs sains ne doivent PAS être entraînés dans l'anomalie.
    assert Sensor.objects.get(house=house, code="V1").calibration_status == "calibrated"


def test_uncalibrated_sensors_do_not_pollute_the_reference(auth_client):
    """Un capteur à 1.0 (jamais calibré) ne doit pas fausser la moyenne."""
    _client, house = auth_client
    _voltage_sensor(house, "V1", 1, 126.5, calibrated=True)
    _voltage_sensor(house, "V2", 2, 129.2, calibrated=True)
    _voltage_sensor(house, "V3", 3, 1.0, calibrated=False)

    calibration.refresh_calibration_status(house)
    # V1/V2 restent corrects malgré la présence d'un capteur non calibré.
    assert Sensor.objects.get(house=house, code="V1").calibration_status == "calibrated"
    assert Sensor.objects.get(house=house, code="V3").calibration_status == "uncalibrated"


def test_voltage_and_current_are_compared_separately(auth_client):
    """Un ZMPT101B et un ZMCT103C n'ont aucune raison d'avoir le même ordre."""
    from django.utils import timezone
    _client, house = auth_client
    _voltage_sensor(house, "V1", 1, 126.5, calibrated=True)
    _voltage_sensor(house, "V2", 2, 129.2, calibrated=True)
    for code, line, factor in [("I1", 1, 0.52), ("I2", 2, 0.55)]:
        Sensor.objects.create(
            house=house, code=code, name=code, sensor_type="current",
            line_number=line, unit="A", calibration_factor=factor,
            calibrated_at=timezone.now(),
        )
    calibration.refresh_calibration_status(house)
    # Aucun suspect : les groupes ne sont pas mélangés.
    assert not Sensor.objects.filter(house=house, calibration_status="suspect").exists()


# --------------------------------------------------------------------------- #
# API : proposer puis confirmer — jamais d'application automatique
# --------------------------------------------------------------------------- #

def test_propose_does_not_persist_anything(auth_client):
    client, house = auth_client
    sensor = _voltage_sensor(house, "V1", 1)

    resp = client.post(
        f"/api/sensors/{sensor.id}/calibration/",
        {"action": "propose", "reference_value": 219.0, "raw_value": 1.84},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["applied"] is False
    assert resp.data["proposed_factor"] == pytest.approx(219.0 / 1.84, rel=1e-4)

    sensor.refresh_from_db()
    assert sensor.calibration_factor == 1.0       # rien enregistré
    assert sensor.calibrated_at is None


def test_apply_persists_after_confirmation(auth_client):
    client, house = auth_client
    sensor = _voltage_sensor(house, "V1", 1)

    resp = client.post(
        f"/api/sensors/{sensor.id}/calibration/",
        {"action": "apply", "calibration_factor": 119.02},
        format="json",
    )
    assert resp.status_code == 200 and resp.data["applied"] is True

    sensor.refresh_from_db()
    assert sensor.calibration_factor == pytest.approx(119.02)
    assert sensor.calibrated_at is not None
    assert sensor.is_calibrated


def test_apply_rejects_zero_factor(auth_client):
    client, house = auth_client
    sensor = _voltage_sensor(house, "V1", 1)
    resp = client.post(
        f"/api/sensors/{sensor.id}/calibration/",
        {"action": "apply", "calibration_factor": 0},
        format="json",
    )
    assert resp.status_code == 400


def test_calibration_converts_raw_to_physical_value(auth_client):
    _client, house = auth_client
    sensor = _voltage_sensor(house, "V1", 1, factor=119.02, calibrated=True)
    assert sensor.apply_calibration(1.84) == pytest.approx(219.0, abs=0.5)


# --------------------------------------------------------------------------- #
# Prototype réel : capteurs, charges, lignes
# --------------------------------------------------------------------------- #

def test_seed_prototype_creates_real_sensors_and_loads(auth_client):
    from django.core.management import call_command
    _client, house = auth_client
    call_command("seed_prototype", house=house.id)

    # 6 capteurs : 3 tensions + 3 courants, chacun sur sa ligne et son GPIO.
    assert Sensor.objects.filter(house=house).count() == 6
    v1 = Sensor.objects.get(house=house, code="V1")
    assert (v1.sensor_type, v1.line_number, v1.gpio_pin, v1.unit) == ("voltage", 1, 34, "V")
    i3 = Sensor.objects.get(house=house, code="I3")
    assert (i3.sensor_type, i3.line_number, i3.gpio_pin, i3.unit) == ("current", 3, 39, "A")
    # Aucun capteur n'est calibré au départ : on ne prétend pas mesurer juste.
    assert not Sensor.objects.filter(house=house).exclude(calibrated_at=None).exists()

    # 5 charges : les lignes 1 et 3 en portent DEUX (lampe + prise) en parallèle.
    loads = Equipment.objects.filter(house=house)
    assert loads.count() == 5
    assert loads.filter(relay_line=1).count() == 2
    assert loads.filter(relay_line=2).count() == 1   # lampe 20 W seule
    assert loads.filter(relay_line=3).count() == 2
    assert loads.get(name="Lampe L2").rated_power_kw == pytest.approx(0.020)
    assert loads.get(name="Prise 1").priority == "NON_CRITICAL"


def test_seed_prototype_is_idempotent(auth_client):
    from django.core.management import call_command
    _client, house = auth_client
    call_command("seed_prototype", house=house.id)
    call_command("seed_prototype", house=house.id)
    assert Sensor.objects.filter(house=house).count() == 6
    assert Equipment.objects.filter(house=house).count() == 5


def test_seed_prototype_preserves_existing_calibration(auth_client):
    """Relancer le seed ne doit pas effacer un coefficient déjà mesuré."""
    from django.core.management import call_command
    from django.utils import timezone
    _client, house = auth_client
    call_command("seed_prototype", house=house.id)

    v1 = Sensor.objects.get(house=house, code="V1")
    v1.calibration_factor = 119.02
    v1.calibrated_at = timezone.now()
    v1.save()

    call_command("seed_prototype", house=house.id)
    v1.refresh_from_db()
    assert v1.calibration_factor == pytest.approx(119.02)
