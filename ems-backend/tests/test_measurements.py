import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.houses.models import House
from apps.measurements.models import Measurement
from apps.mqtt_handler.handlers import handle_message, validate_payload

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client():
    user = User.objects.create_user("bob", "b@x.com", "pass12345")
    house = House.objects.create(owner=user, name="Maison Test")
    client = APIClient()
    client.force_authenticate(user)
    return client, house


def test_create_and_list_measurement(auth_client):
    client, house = auth_client
    resp = client.post(
        "/api/measurements/",
        {
            "house": house.id,
            "measurement_type": "production",
            "value": 3.4,
            "unit": "kW",
            "timestamp": timezone.now().isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    assert client.get("/api/measurements/").data["count"] == 1


def test_mqtt_payload_validation():
    ok, _ = validate_payload({"type": "production", "value": 2.0})
    assert ok
    bad, msg = validate_payload({"value": 2.0})
    assert not bad


def test_mqtt_handle_creates_measurement():
    user = User.objects.create_user("c", "c@x.com", "pass12345")
    house = House.objects.create(owner=user, name="H")
    m = handle_message(house.id, {"type": "production", "value": 1.2})
    assert m is not None
    assert Measurement.objects.count() == 1
