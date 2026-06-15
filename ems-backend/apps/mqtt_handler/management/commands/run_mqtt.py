"""
Management command running the MQTT subscriber loop.

Usage:  python manage.py run_mqtt

Subscribes to:
  ems/{house_id}/sensors/{sensor_id}/data
  ems/{house_id}/battery/data
  ems/{house_id}/status
"""
import json
import logging

import paho.mqtt.client as mqtt
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.mqtt_handler.handlers import handle_message

logger = logging.getLogger(__name__)

TOPICS = [
    ("ems/+/sensors/+/data", 0),
    ("ems/+/battery/data", 0),
    ("ems/+/status", 0),
]


def _house_id_from_topic(topic: str):
    parts = topic.split("/")
    # ems/{house_id}/...
    if len(parts) >= 2 and parts[0] == "ems":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


class Command(BaseCommand):
    help = "Run the MQTT subscriber and persist incoming measurements."

    def handle(self, *args, **options):
        client = mqtt.Client()
        if settings.MQTT_USERNAME:
            client.username_pw_set(
                settings.MQTT_USERNAME, settings.MQTT_PASSWORD
            )

        client.on_connect = self._on_connect
        client.on_message = self._on_message

        self.stdout.write(
            f"Connexion au broker MQTT {settings.MQTT_BROKER}:{settings.MQTT_PORT}…"
        )
        client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
        client.loop_forever()

    def _on_connect(self, client, userdata, flags, rc):
        self.stdout.write(self.style.SUCCESS(f"Connecté (rc={rc}). Souscription…"))
        for topic, qos in TOPICS:
            client.subscribe(topic, qos)

    def _on_message(self, client, userdata, msg):
        if msg.topic.endswith("/status"):
            return  # status frames are not measurements
        house_id = _house_id_from_topic(msg.topic)
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("MQTT: payload illisible sur %s: %s", msg.topic, exc)
            return
        handle_message(house_id, payload)
