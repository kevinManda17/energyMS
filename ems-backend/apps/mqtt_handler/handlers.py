"""
Payload validation + persistence for incoming MQTT messages.

Kept framework-agnostic so it can be unit-tested without a live broker.
"""
import logging

from django.utils.dateparse import parse_datetime
from django.utils import timezone

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"type", "value"}
VALID_TYPES = {
    "production",
    "consumption",
    "battery_soc",
    "voltage",
    "current",
    "power",
    "temperature",
}


def validate_payload(payload: dict):
    """Return (ok, error_message)."""
    if not isinstance(payload, dict):
        return False, "Payload doit être un objet JSON."
    missing = REQUIRED_FIELDS - payload.keys()
    if missing:
        return False, f"Champs manquants: {sorted(missing)}"
    if payload["type"] not in VALID_TYPES:
        return False, f"type invalide: {payload['type']}"
    try:
        float(payload["value"])
    except (TypeError, ValueError):
        return False, "value doit être numérique."
    return True, ""


def handle_message(house_id: int, payload: dict):
    """Validate a payload and create a Measurement. Returns the object or None."""
    from apps.houses.models import House
    from apps.measurements.models import Measurement

    ok, error = validate_payload(payload)
    if not ok:
        logger.warning("MQTT payload rejeté (house=%s): %s", house_id, error)
        return None

    house = House.objects.filter(pk=house_id).first()
    if house is None:
        logger.warning("MQTT: maison %s introuvable.", house_id)
        return None

    ts = parse_datetime(payload["timestamp"]) if payload.get("timestamp") else None
    measurement = Measurement.objects.create(
        house=house,
        sensor_id=payload.get("sensor_id"),
        measurement_type=payload["type"],
        value=float(payload["value"]),
        unit=payload.get("unit", "kW"),
        timestamp=ts or timezone.now(),
    )
    logger.info(
        "MQTT: mesure enregistrée house=%s type=%s value=%s",
        house_id,
        payload["type"],
        payload["value"],
    )
    return measurement
