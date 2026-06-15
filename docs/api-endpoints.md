# Endpoints API

Base URL : `http://localhost:8000/api`
Auth : `Authorization: Bearer <access_token>` (sauf register/login et pages publiques).

## Auth
| Méthode | Endpoint              | Description            |
|---------|-----------------------|------------------------|
| POST    | `/auth/register/`     | Création de compte     |
| POST    | `/auth/login/`        | Login → access+refresh |
| POST    | `/auth/refresh/`      | Rafraîchir le token    |
| GET     | `/auth/me/`           | Profil courant         |

**Login**
```json
POST /api/auth/login/
{ "username": "demo", "password": "demo12345" }
→ { "access": "...", "refresh": "..." }
```

## Houses
`GET/POST /api/houses/` · `GET/PUT/DELETE /api/houses/{id}/`

## Devices
| Méthode | Endpoint                          |
|---------|-----------------------------------|
| GET/POST| `/houses/{id}/sensors/`           |
| GET/POST| `/houses/{id}/equipment/`         |
| PUT/DEL | `/equipment/{id}/`                |

## Measurements
| Méthode | Endpoint                     | Description                    |
|---------|------------------------------|--------------------------------|
| POST    | `/measurements/`             | Créer une mesure               |
| GET     | `/measurements/`             | Liste (filtres house/type)     |
| GET     | `/measurements/latest/`      | Dernières valeurs par type     |
| GET     | `/measurements/history/`     | Historique paginé (start/end)  |

```json
POST /api/measurements/
{ "house": 1, "measurement_type": "production", "value": 3.42, "unit": "kW",
  "timestamp": "2026-05-17T19:40:00Z" }
```

## Datasets
`POST /api/datasets/import/` (multipart : `name`, `kind`, `file`) · `GET /api/datasets/`

## Forecasting
| Méthode | Endpoint                          | Description                 |
|---------|-----------------------------------|-----------------------------|
| POST    | `/forecasting/train/`             | `{ "target": "production" }`|
| GET     | `/forecasting/predict/`           | `?target=&hours=&house=`    |
| GET     | `/forecasting/predictions/`       | Historique des prévisions   |
| GET     | `/forecasting/models/`            | Modèles + métriques         |

## Decisions
| Méthode | Endpoint                  | Description                      |
|---------|---------------------------|----------------------------------|
| POST    | `/decisions/trigger/`     | Exécute le moteur flou           |
| GET     | `/decisions/`             | Historique                       |
| GET     | `/decisions/latest/`      | Dernière décision                |
| GET     | `/decisions/{id}/`        | Détail (règles activées…)        |

```json
POST /api/decisions/trigger/
{ "house": 1, "production_pv": 0.4, "consommation": 4.0, "batterie_soc": 18 }
→ { "action": "DELESTER_NON_PRIORITAIRES", "confidence_score": 0.7, ... }
```

## Alerts
`GET /api/alerts/` · `GET /api/alerts/unread/` · `POST /api/alerts/{id}/acknowledge/`

## Reports
`GET /api/reports/daily/?house=&date=` · `GET /api/reports/export/csv/`

## Documentation
`GET /api/schema/` (OpenAPI) · `GET /api/docs/` (Swagger UI)
