"""La tension affichée est conditionnée dans la plage plausible [215, 224] V."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.devices.models import RelayState
from apps.devices.views import condition_voltage
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_condition_voltage_clamps_live_readings():
    assert condition_voltage(269) == 224      # trop haut -> plafonné
    assert condition_voltage(252) == 224
    assert condition_voltage(200) == 215      # trop bas mais secteur présent -> planché
    assert condition_voltage(219) == 219      # déjà dans la plage -> inchangé
    assert condition_voltage(0) == 0          # ligne coupée -> pas maquillée
    assert condition_voltage(None) is None


def test_stored_network_voltage_is_in_band():
    user = User.objects.create_user("v", "v@x.com", "pass12345")
    house = House.objects.create(owner=user, name="Proto")
    state = RelayState.objects.create(house=house)

    esp = APIClient()
    resp = esp.post(
        f"/api/ems/decision/?token={state.device_token}",
        {
            "line1": {"voltage": 269, "current": 1, "power": 0.2},
            "line2": {"voltage": 252, "current": 1, "power": 0.2},
            "line3": {"voltage": 260, "current": 1, "power": 0.2},
        },
        format="json",
    )
    assert resp.status_code == 200
    v = Measurement.objects.filter(house=house, measurement_type="voltage").first()
    assert v is not None
    assert 215.0 <= v.value <= 224.0
