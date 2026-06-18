# Architecture EMS

## Vue globale

```
                ┌─────────────┐      ┌──────────────┐
   Capteurs ───▶│  Mosquitto  │─────▶│ mqtt_worker  │
   IoT / sim    │   (MQTT)    │      │  (Django)    │
                └─────────────┘      └──────┬───────┘
                       │                    ▼
                       │            ┌────────────────┐    ┌────────────┐
   Edge Gateway ◀──────┘            │  Django REST   │◀──▶│ PostgreSQL │
   (Raspberry Pi)                   │     API        │    └────────────┘
        │  cache + sync             └───┬────────┬───┘
        ▼                               │        │
   API locale FastAPI         React Web │        │ React Native (Expo)
        ▲                               ▼        ▼
        └──────── mode edge ──────  Frontend   Mobile
```

## Modules backend

| App            | Rôle                                                    |
|----------------|---------------------------------------------------------|
| `users`        | Auth JWT, rôles USER/ADMIN, profil                      |
| `houses`       | Maisons / micro-réseaux                                 |
| `devices`      | Capteurs et équipements (charges)                       |
| `measurements` | Mesures IoT (production, conso, batterie, tension…)     |
| `datasets`     | Import CSV/JSON admin/interne, hors parcours utilisateur |
| `forecasting`  | Prévisions horaires production PV + consommation        |
| `fuzzy_engine` | Système expert flou + décisions                         |
| `alerts`       | Alertes critiques / warning / info                      |
| `reports`      | Rapports journaliers + export CSV                       |
| `mqtt_handler` | Souscripteur MQTT + persistance des mesures            |

## Flux IoT
1. Un capteur publie sur `ems/{house_id}/sensors/{sensor_id}/data`.
2. `mqtt_worker` (commande `run_mqtt`) valide le payload et crée une `Measurement`.
3. Le frontend/mobile lisent les mesures via l'API REST.

## Flux prédiction
1. `GET /api/forecasting/predict/?target=production&hours=24&house=ID` calcule les horizons à venir.
2. Les points sont enregistrés dans `Prediction` pour alimenter le mobile, le web et le moteur flou.
3. `POST /api/forecasting/train/` reste un endpoint admin/interne de compatibilité, sans entraînement depuis la plateforme.

## Flux décision
1. `POST /api/decisions/trigger/` lit les dernières mesures (ou valeurs fournies).
2. Le moteur flou évalue les règles → action + confiance + règles activées.
3. Si l'action est critique → une `Alert` est créée automatiquement.
