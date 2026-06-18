# EMS — Energy Management System

Plateforme de **gestion énergétique pour micro-réseau domestique intelligent** :
supervision IoT, prévisions horaires production/consommation, système expert flou, supervision
web React, application mobile React Native et passerelle Edge.

> L'agent conversationnel n'est **pas** développé dans cette version (perspective
> future — voir `docs/future-agent.md`).

## Stack
| Couche | Technologies |
|--------|--------------|
| Backend | Django REST Framework, PostgreSQL, SimpleJWT, paho-mqtt, scikit-learn, scikit-fuzzy, drf-spectacular |
| Frontend | React 18, Vite, Tailwind, React Router, TanStack Query, Zustand, Recharts, Lucide |
| Mobile | React Native Expo, React Navigation, Zustand, AsyncStorage, Expo Notifications |
| Edge | Python, paho-mqtt, httpx, SQLite, FastAPI |
| Infra | Docker, Docker Compose, Nginx, Mosquitto, Vercel, AWS |

## Structure
```
ems-platform/
├── ems-backend/     # API Django REST (10 apps)
├── ems-frontend/    # Dashboard React (Vite)
├── ems-mobile/      # App Expo (cloud/edge/cache)
├── edge-gateway/    # Passerelle Raspberry Pi
├── mqtt/            # mosquitto.conf
├── nginx/           # reverse proxy
├── infra/           # notes AWS + Vercel
├── docs/            # architecture, API, fuzzy, déploiement…
├── docker-compose.yml / docker-compose.prod.yml
```

## Démarrage rapide (Docker)
```bash
cd ems-platform
docker compose up --build
```
- Frontend : http://localhost:5173
- API : http://localhost:8000/api · Swagger : http://localhost:8000/api/docs/
- Comptes seedés : `admin / admin12345` et `demo / demo12345`

Le service backend exécute automatiquement `migrate` + `seed_initial_data`
(données réalistes : maisons, capteurs, équipements, mesures, prévisions, décisions, alertes).

## Démarrage manuel (sans Docker)

### Backend
```bash
cd ems-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # sans DATABASE_URL → SQLite
python manage.py migrate
python manage.py seed_initial_data
python manage.py runserver
# (autre terminal) souscripteur MQTT :
python manage.py run_mqtt
```

### Frontend
```bash
cd ems-frontend
npm install
cp .env.example .env
npm run dev          # http://localhost:5173
```

### Mobile
```bash
cd ems-mobile
npm install
cp .env.example .env
npm start            # Expo
```

### Edge gateway
```bash
cd edge-gateway
pip install -r requirements.txt
cp .env.example .env
python mqtt_subscriber.py            # cache MQTT → SQLite
uvicorn sync_service:app --port 8001 # API locale + sync
```

## Tester l'API
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo12345"}'

# Déclencher une décision (avec le token)
curl -X POST http://localhost:8000/api/decisions/trigger/ \
  -H "Authorization: Bearer <ACCESS>" -H "Content-Type: application/json" \
  -d '{"house":1,"production_pv":0.4,"consommation":4.0,"batterie_soc":18}'
```

## Tests
```bash
cd ems-backend && pytest          # backend
cd ems-frontend && npm test       # frontend (vitest)
cd ems-mobile && npm test         # mobile (jest)
```

## Déploiement
Voir `docs/deployment.md`, `infra/vercel/` (frontend) et `infra/aws/` (backend prod).

## URLs utiles
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api |
| Swagger | http://localhost:8000/api/docs/ |
| Admin Django | http://localhost:8000/admin/ |
| Edge API | http://localhost:8001/health |
