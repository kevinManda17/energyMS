# EMS - Energy Management System

Plateforme de gestion energetique pour micro-reseau domestique intelligent : supervision IoT, actifs energetiques, previsions par modeles importes/fallback horaire, systeme expert flou, dashboard React, application mobile React Native et passerelle Edge.

> L'agent conversationnel n'est pas developpe dans cette version. Il reste une perspective future, voir `docs/future-agent.md`.

## Stack

| Couche | Technologies |
| --- | --- |
| Backend | Django REST Framework, PostgreSQL, SimpleJWT, paho-mqtt, scikit-learn/joblib, drf-spectacular |
| Frontend | React 18, Vite, Tailwind, React Router, TanStack Query, Zustand, Recharts, Lucide |
| Mobile | React Native Expo, React Navigation, Zustand, AsyncStorage, Expo Notifications |
| Edge | Python, paho-mqtt, httpx, SQLite, FastAPI |
| Infra | Docker, Docker Compose, Nginx, Mosquitto, Vercel, AWS |

## Structure

```text
ems-platform/
  ems-backend/     API Django REST
  ems-frontend/    Dashboard React Vite
  ems-mobile/      App Expo cloud/edge/local
  edge-gateway/    Passerelle Raspberry Pi
  mqtt/            Configuration Mosquitto
  nginx/           Reverse proxy
  infra/           Notes AWS et Vercel
  docs/            Architecture, API, fuzzy, deploiement
```

## Modele EMS actuel

Le backend suit la chaine :

```text
collecte IoT -> mesures -> modeles pre-entraines importes -> prevision -> decision floue -> alerte -> supervision
```

`House` represente le micro-reseau logique. Les panneaux PV, batteries, onduleurs et autres composants physiques sont dans `EnergyAsset`. Le forecasting n'entraine pas de modele depuis la plateforme : il importe des modeles pre-entraines et utilise `HourlyProfileForecast` comme fallback.

## Demarrage rapide avec Docker

```bash
cd ems-platform
docker compose up --build
```

- Frontend : http://localhost:5173
- API : http://localhost:8000/api
- Swagger : http://localhost:8000/api/docs/
- Comptes seedes : `admin / admin12345` et `demo / demo12345`

Le service backend execute automatiquement `migrate` + `seed_initial_data` avec donnees realistes : maisons, actifs energetiques, capteurs, equipements, mesures, previsions, decisions et alertes.

## Demarrage manuel sans Docker

### Backend

```bash
cd ems-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_initial_data
python manage.py runserver
```

Souscripteur MQTT dans un autre terminal :

```bash
python manage.py run_mqtt
```

### Frontend

```bash
cd ems-frontend
npm install
copy .env.example .env
npm run dev
```

### Mobile

```bash
cd ems-mobile
npm install
copy .env.example .env
npm start
```

### Edge gateway

```bash
cd edge-gateway
pip install -r requirements.txt
copy .env.example .env
python mqtt_subscriber.py
uvicorn sync_service:app --port 8001
```

## API rapide

Login :

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo12345"}'
```

Declencher une decision :

```bash
curl -X POST http://localhost:8000/api/decisions/trigger/ \
  -H "Authorization: Bearer <ACCESS>" \
  -H "Content-Type: application/json" \
  -d '{"house":1,"production_pv":0.4,"consommation":4.0,"batterie_soc":18}'
```

## Tests

```bash
cd ems-backend && pytest
cd ems-frontend && npm test
cd ems-mobile && npm test
```

## Documentation

- `docs/architecture.md`
- `docs/api-endpoints.md`
- `docs/environment-variables.md`
- `docs/fuzzy-system.md`
- `docs/deployment.md`
- `docs/development-roadmap.md`

## URLs utiles

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api |
| Swagger | http://localhost:8000/api/docs/ |
| Admin Django | http://localhost:8000/admin/ |
| Edge API | http://localhost:8001/health |
