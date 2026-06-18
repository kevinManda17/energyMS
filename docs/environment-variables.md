# Variables d'environnement

## Backend (`ems-backend/.env`)

| Variable | Exemple | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | `change-me-in-production` | Cle secrete Django |
| `DJANGO_DEBUG` | `True` | Mode debug |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,172.20.10.2` | Hotes autorises |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | Settings actifs |
| `DATABASE_URL` | `postgresql://ems_user:ems_password@db:5432/ems_db` | Base de donnees |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Origines CORS |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `60` | Duree de vie access token |
| `MQTT_BROKER` / `MQTT_PORT` | `mqtt` / `1883` | Broker MQTT |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | | Auth broker optionnelle |
| `SMS_PROVIDER` | `console` | Provider SMS, fallback dev |
| `SMS_API_KEY` | | Cle provider SMS |
| `SMS_SENDER` | `EMS` | Expediteur SMS |

Sans `DATABASE_URL`, le backend bascule sur SQLite en local.

## Frontend (`ems-frontend/.env`)

| Variable | Exemple |
|----------|---------|
| `VITE_API_BASE_URL` | `http://localhost:8000/api` |
| `VITE_WS_URL` | `ws://localhost:8000/ws` |
| `VITE_APP_NAME` | `EMS Dashboard` |

## Mobile (`ems-mobile/.env`)

| Variable | Exemple |
|----------|---------|
| `EXPO_PUBLIC_API_BASE_URL` | `http://172.20.10.2:8000/api` |
| `EXPO_PUBLIC_EDGE_API_URL` | `http://172.20.10.2:8000/api` |
| `EXPO_PUBLIC_APP_NAME` | `EMS Mobile` |

## Edge (`edge-gateway/.env`)

| Variable | Exemple |
|----------|---------|
| `EDGE_MQTT_BROKER` / `EDGE_MQTT_PORT` | `localhost` / `1883` |
| `EDGE_BACKEND_API_URL` | `http://localhost:8000/api` |
| `EDGE_SYNC_INTERVAL_SECONDS` | `30` |
| `EDGE_DB_PATH` | `edge_cache.db` |
| `EDGE_API_PORT` | `8001` |
