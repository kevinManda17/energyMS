# Endpoints API

Base URL: `http://localhost:8000/api`

Auth: `Authorization: Bearer <access_token>`, sauf inscription, connexion, verification telephone, verification e-mail et reset password.

## Auth

| Methode | Endpoint | Description |
| --- | --- | --- |
| POST | `/auth/register/` | Creation de compte avec confirmation de mot de passe |
| POST | `/auth/login/` | Connexion JWT |
| POST | `/auth/refresh/` | Rafraichir le token |
| GET/PATCH | `/auth/me/` | Profil courant |
| POST | `/auth/phone/send-code/` | Envoyer un code de verification telephone |
| POST | `/auth/phone/verify-code/` | Verifier le code telephone |
| POST | `/auth/email/verify/request/` | Demander un e-mail de verification |
| POST | `/auth/email/verify/confirm/` | Confirmer la verification e-mail |
| POST | `/auth/password/reset/request/` | Demander la reinitialisation du mot de passe |
| POST | `/auth/password/reset/confirm/` | Confirmer la reinitialisation du mot de passe |
| POST | `/auth/password/change/` | Changer le mot de passe connecte |

## Houses

| Methode | Endpoint | Description |
| --- | --- | --- |
| GET/POST | `/houses/` | Lister/creer les micro-reseaux |
| GET/PUT/PATCH/DELETE | `/houses/{id}/` | Detail et modification |

## Energy assets

| Methode | Endpoint | Description |
| --- | --- | --- |
| GET/POST | `/energy-assets/` | CRUD des actifs energetiques accessibles |
| GET/PUT/PATCH/DELETE | `/energy-assets/{id}/` | Detail actif energetique |
| GET/POST | `/houses/{id}/energy-assets/` | Actifs d'une maison |

Types principaux : `PV_PANEL`, `BATTERY`, `INVERTER`, `SOLAR_CONTROLLER`, `GRID_SOURCE`, `GENERATOR`.

## Devices

| Methode | Endpoint | Description |
| --- | --- | --- |
| GET/POST | `/houses/{id}/sensors/` | Capteurs d'une maison, lien optionnel vers `energy_asset` |
| GET/POST | `/houses/{id}/equipment/` | Equipements/charges d'une maison |
| GET/PUT/PATCH/DELETE | `/equipment/{id}/` | Detail equipement |
| GET/PATCH | `/houses/{id}/relays/` | Etat commande des 3 lignes du prototype (`line1/2/3`, `device_token`) |
| POST | `/ems/decision/?token=` | Sondage du noeud ESP32 : recoit les mesures, renvoie `L1=x;L2=x;L3=x` |

Le noeud ESP32 interroge `/ems/decision/` toutes les ~3 s. Sans jeton, il suit
le micro-reseau le plus recemment pilote depuis l'interface (liaison auto). Le
releve 3-lignes recu (`{"line1":{voltage,current,power},...}`) est persiste
comme mesures reelles du micro-reseau (consommation, tension, courant), toutes
les 30 s, ce qui alimente le moteur expert en temps quasi reel.

## Measurements

| Methode | Endpoint | Description |
| --- | --- | --- |
| POST | `/measurements/` | Creer une mesure |
| GET | `/measurements/` | Liste filtree par `house`, `sensor`, `measurement_type` |
| GET | `/measurements/latest/` | Dernieres valeurs par type (marque le micro-reseau comme actif) |
| GET | `/measurements/history/` | Historique pagine avec `start`/`end` |
| POST | `/measurements/weather/collect/` | Lance la collecte Open-Meteo (non-bloquant, `202`) |
| GET | `/measurements/weather/status/` | Derniere meteo collectee + etat de la collecte auto |

Types supportes : `production`, `consumption`, `battery_soc`, `voltage`, `current`, `power`, `temperature`, `luminosity`, `irradiance` (+ variables meteo/PV derivees).

Sources reelles des mesures : le noeud ESP32 (via `/ems/decision/`) pour
consommation/tension/courant, et Open-Meteo pour la meteo/irradiance. La
collecte meteo automatique ne vise que les micro-reseaux consultes recemment
(fenetre `WEATHER_ACTIVE_WINDOW_MINUTES`), et non plus toutes les maisons.

## Forecasting

| Methode | Endpoint | Description |
| --- | --- | --- |
| POST | `/forecasting/models/import/` | Importer un modele pre-entraine, admin uniquement |
| GET | `/forecasting/models/` | Lister les modeles importes/fallback |
| POST/GET | `/forecasting/predict/` | Produire et stocker des previsions |
| GET | `/forecasting/forecasts/` | Historique des previsions |
| GET | `/forecasting/forecasts/latest/` | Derniere prevision |

Le backend ne propose pas d'endpoint d'entrainement utilisateur : les modeles sont entraines hors-ligne puis enregistres via `python manage.py register_models` (lit `ems-backend/ml_models/`). Modeles actifs par defaut : **GRU** (consommation), **Random Forest** (production ; le LSTM reste enregistre en reference). En l'absence de modele actif pour une cible, la prevision ne renvoie pas d'estimation de repli : une erreur explicite est levee.

## Decisions

| Methode | Endpoint | Description |
| --- | --- | --- |
| POST | `/decisions/trigger/` | Evaluation du systeme expert |
| GET | `/decisions/` | Historique |
| GET | `/decisions/latest/` | Derniere decision |
| GET | `/decisions/{id}/` | Detail avec regles, faits d'entree et prevision liee |

## Alerts

| Methode | Endpoint | Description |
| --- | --- | --- |
| GET | `/alerts/` | Alertes accessibles |
| GET | `/alerts/unread/` | Alertes non lues |
| POST | `/alerts/{id}/acknowledge/` | Marquer comme lue |

## Reports et exports

| Methode | Endpoint | Description |
| --- | --- | --- |
| GET | `/reports/daily/?house=&date=` | Resume journalier |
| GET | `/reports/summary/?house=&days=` | Agregation journaliere d'energie (kWh) par integration trapezoidale des mesures de puissance |
| GET | `/reports/export/csv/?house=&type=` | Export CSV `measurements`, `forecasts`, `decisions` ou `full` |
| GET | `/reports/exports/` | Historique `DataExport` |

## Documentation

| Methode | Endpoint | Description |
| --- | --- | --- |
| GET | `/schema/` | Schema OpenAPI |
| GET | `/docs/` | Swagger UI |
