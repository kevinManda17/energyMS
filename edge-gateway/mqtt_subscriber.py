"""
Edge MQTT subscriber.

Listens to the local Mosquitto broker and stores every valid measurement
in the local SQLite cache. The sync_service then pushes them to the cloud.
"""
import json
import logging
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

import local_cache

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edge.mqtt")

BROKER = os.getenv("EDGE_MQTT_BROKER", "localhost")
PORT = int(os.getenv("EDGE_MQTT_PORT", "1883"))
TOPICS = [("ems/+/sensors/+/data", 0), ("ems/+/battery/data", 0)]


def _house_id(topic):
    parts = topic.split("/")
    try:
        return int(parts[1])
    except (IndexError, ValueError):
        return None


def on_connect(client, userdata, flags, rc):
    logger.info("Connecté au broker (rc=%s).", rc)
    for topic, qos in TOPICS:
        client.subscribe(topic, qos)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Payload illisible sur %s", msg.topic)
        return
    house_id = _house_id(msg.topic)
    local_cache.save_measurement(house_id, json.dumps(payload))
    logger.info("Mesure mise en cache (house=%s).", house_id)


def main():
    local_cache.init_db()
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    logger.info("Connexion MQTT %s:%s…", BROKER, PORT)
    client.connect(BROKER, PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
