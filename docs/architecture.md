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
| `datasets`     | Import CSV/JSON pour l'entraînement ML                  |
| `forecasting`  | Random Forest (production PV + consommation)            |
| `fuzzy_engine` | Système expert flou + décisions                         |
| `alerts`       | Alertes critiques / warning / info                      |
| `reports`      | Rapports journaliers + export CSV                       |
| `mqtt_handler` | Souscripteur MQTT + persistance des mesures            |

## Flux IoT
1. Un capteur publie sur `ems/{house_id}/sensors/{sensor_id}/data`.
2. `mqtt_worker` (commande `run_mqtt`) valide le payload et crée une `Measurement`.
3. Le frontend/mobile lisent les mesures via l'API REST.

## Flux prédiction
1. `POST /api/forecasting/train/` entraîne un Random Forest (dataset ou données synthétiques).
2. Le modèle est sauvegardé via `joblib` (`ml_models/`).
3. `GET /api/forecasting/predict/` renvoie les prévisions horaires + métriques (MAE/RMSE/R²).

## Flux décision
1. `POST /api/decisions/trigger/` lit les dernières mesures (ou valeurs fournies).
2. Le moteur flou évalue les règles → action + confiance + règles activées.
3. Si l'action est critique → une `Alert` est créée automatiquement.
