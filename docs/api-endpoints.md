# Endpoints API

Base URL: `http://localhost:8000/api`

Auth: `Authorization: Bearer <access_token>`, sauf inscription, connexion et verification telephone.

## Auth

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/register/` | Creation de compte avec confirmation de mot de passe |
| POST | `/auth/login/` | Connexion JWT |
| POST | `/auth/refresh/` | Rafraichir le token |
| GET/PATCH | `/auth/me/` | Profil courant |
| POST | `/auth/phone/send-code/` | Envoyer un code de verification telephone |
| POST | `/auth/phone/verify-code/` | Verifier le code telephone |
| POST | `/auth/password/change/` | Changer le mot de passe |

## Houses

`GET/POST /api/houses/`

`GET/PUT/DELETE /api/houses/{id}/`

## Devices

| Methode | Endpoint |
|---------|----------|
| GET/POST | `/houses/{id}/sensors/` |
| GET/POST | `/houses/{id}/equipment/` |
| GET/PUT/DELETE | `/equipment/{id}/` |

## Measurements

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/measurements/` | Creer une mesure |
| GET | `/measurements/` | Liste filtree |
| GET | `/measurements/latest/` | Dernieres valeurs par type |
| GET | `/measurements/history/` | Historique pagine |

## Forecasting

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/forecasting/train/` | Admin/interne uniquement, compatibilite |
| GET | `/forecasting/predict/?target=&hours=&house=` | Previsions horaires a venir |
| GET | `/forecasting/predictions/` | Historique des previsions |
| GET | `/forecasting/models/` | Strategie active de prevision |

## Decisions

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/decisions/trigger/` | Evaluation du systeme expert |
| GET | `/decisions/` | Historique |
| GET | `/decisions/latest/` | Derniere decision |
| GET | `/decisions/{id}/` | Detail avec regles et faits d'entree |

## Alerts

`GET /api/alerts/`

`GET /api/alerts/unread/`

`POST /api/alerts/{id}/acknowledge/`

## Reports

`GET /api/reports/daily/?house=&date=`

`GET /api/reports/export/csv/`

## Documentation

`GET /api/schema/`

`GET /api/docs/`
