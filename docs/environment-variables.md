# Variables d'environnement

## Backend (`ems-backend/.env`)

| Variable | Exemple | Description |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | `change-me-in-production` | Cle secrete Django |
| `DJANGO_DEBUG` | `True` | Mode debug |
| `DJANGO_ALLOWED_HOSTS` | `192.168.0.117,localhost,127.0.0.1` | Hotes autorises |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | Settings actifs |
| `DATABASE_URL` | `postgresql://ems_user:ems_password@db:5432/ems_db` | Base de donnees |
| `CORS_ALLOWED_ORIGINS` | `http://192.168.0.117:5173` | Origines CORS |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `60` | Duree de vie access token |
| `MQTT_BROKER` / `MQTT_PORT` | `mqtt` / `1883` | Broker MQTT |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | | Auth broker optionnelle |
| `SMS_PROVIDER` | `console` | Provider SMS, fallback dev |
| `SMS_API_KEY` | | Cle provider SMS |
| `SMS_SENDER` | `EMS` | Expediteur SMS |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Backend e-mail |
| `EMAIL_HOST` / `EMAIL_PORT` | `smtp.example.com` / `587` | Serveur SMTP |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | | Identifiants SMTP |
| `EMAIL_USE_TLS` | `True` | TLS SMTP |
| `DEFAULT_FROM_EMAIL` | `noreply@ems.local` | Expediteur e-mail |
| `FRONTEND_URL` | `http://192.168.0.117:5173` | URL utilisee dans les liens e-mail |
| `PASSWORD_RESET_TOKEN_MINUTES` | `30` | Duree de validite reset password |
| `EMAIL_VERIFICATION_TOKEN_MINUTES` | `60` | Duree de validite verification e-mail |
| `WEATHER_AUTO_COLLECT` | `1` | Active la collecte meteo de fond (`0` pour desactiver) |
| `WEATHER_COLLECT_INTERVAL_MINUTES` | `2` | Cadence de la collecte meteo automatique |
| `WEATHER_ACTIVE_WINDOW_MINUTES` | `15` | Ne collecte que les micro-reseaux consultes dans cette fenetre |
| `WEATHER_LATITUDE` / `WEATHER_LONGITUDE` | `-4.3276` / `15.3136` | Coordonnees de repli si un micro-reseau n'a pas les siennes |

Sans `DATABASE_URL`, le backend bascule sur SQLite en local.

## Frontend (`ems-frontend/.env`)

| Variable | Exemple |
| --- | --- |
| `VITE_API_BASE_URL` | `http://192.168.0.117:8000/api` |
| `VITE_WS_URL` | `ws://192.168.0.117:8000/ws` |
| `VITE_APP_NAME` | `EMS Dashboard` |

## Mobile (`ems-mobile/.env`)

| Variable | Exemple |
| --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | `http://192.168.0.117:8000/api` |
| `EXPO_PUBLIC_EDGE_API_URL` | `http://192.168.0.117:8000/api` |
| `EXPO_PUBLIC_APP_NAME` | `EMS Mobile` |

## Edge (`edge-gateway/.env`)

| Variable | Exemple |
| --- | --- |
| `EDGE_MQTT_BROKER` / `EDGE_MQTT_PORT` | `localhost` / `1883` |
| `EDGE_BACKEND_API_URL` | `http://192.168.0.117:8000/api` |
| `EDGE_SYNC_INTERVAL_SECONDS` | `30` |
| `EDGE_DB_PATH` | `edge_cache.db` |
| `EDGE_API_PORT` | `8001` |
