# EMS Edge Gateway

Passerelle locale destinée à un **Raspberry Pi** (ou tout hôte local) pour une
exécution partielle hors-ligne du système EMS.

## Rôle

- Réception MQTT locale depuis Mosquitto (`mqtt_subscriber.py`)
- Cache local SQLite (`local_cache.py`) — résilient si le cloud est indisponible
- Synchronisation périodique vers le backend cloud (`sync_service.py`)
- Petite API locale FastAPI pour que le mobile lise les dernières mesures en LAN

## Architecture

```
Capteurs IoT → MQTT (Mosquitto) → mqtt_subscriber → SQLite (cache)
                                                       │
                              sync_service ── (HTTP) ──┴──→ Backend cloud
                                   │
                              FastAPI local ──→ App mobile (mode edge)
```

## Lancer

```bash
cp .env.example .env
pip install -r requirements.txt

# 1) Souscripteur MQTT (met en cache les mesures)
python mqtt_subscriber.py

# 2) API locale + boucle de synchronisation
uvicorn sync_service:app --host 0.0.0.0 --port 8001
```

### Avec Docker

```bash
docker build -t ems-edge .
docker run --env-file .env -p 8001:8001 ems-edge
```

## API locale

| Méthode | Endpoint                  | Description                       |
|---------|---------------------------|-----------------------------------|
| GET     | `/health`                 | État + nombre de mesures en attente |
| GET     | `/measurements/latest/`   | Dernières mesures en cache        |

Le mobile peut pointer dessus via le **mode Edge** (`EXPO_PUBLIC_EDGE_API_URL`).

## Notes

Squelette volontairement simple et extensible — pas une solution industrielle.
Évolutions possibles : buffering par lot, compression, TLS MQTT, file d'attente
persistante, reprise après coupure prolongée.
