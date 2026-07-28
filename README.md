# EMS - Energy Management System

Plateforme de gestion energetique pour micro-reseau domestique intelligent : supervision IoT, actifs energetiques, previsions par modeles ML pre-entraines (GRU consommation, Random Forest production), systeme expert flou, dashboard React, application mobile React Native et passerelle Edge.

[![Web App](https://img.shields.io/badge/Web-energyms.vercel.app-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://energyms.vercel.app)
[![Backend API](https://img.shields.io/badge/Backend-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://energy-backend.up.railway.app/api/docs/)
[![Database](https://img.shields.io/badge/DB-Neon%20PostgreSQL-00E599?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech)

> L'agent conversationnel n'est pas developpe dans cette version. Il reste une perspective future, voir `docs/future-agent.md`.

## Technologies

**Backend & API**

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?logo=django&logoColor=white)
![Django REST](https://img.shields.io/badge/DRF-A30000?logo=django&logoColor=white)
![SimpleJWT](https://img.shields.io/badge/JWT-000000?logo=jsonwebtokens&logoColor=white)
![MQTT](https://img.shields.io/badge/MQTT-660066?logo=mqtt&logoColor=white)
![Mosquitto](https://img.shields.io/badge/Mosquitto-3C5280?logo=eclipsemosquitto&logoColor=white)

**IA / Machine Learning**

![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?logo=tensorflow&logoColor=white)
![Keras](https://img.shields.io/badge/Keras-D00000?logo=keras&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white)
![Open-Meteo](https://img.shields.io/badge/Open--Meteo-API-0A9396)

**Frontend web**

![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-06B6D4?logo=tailwindcss&logoColor=white)
![TanStack Query](https://img.shields.io/badge/TanStack%20Query-FF4154?logo=reactquery&logoColor=white)

**Mobile**

![React Native](https://img.shields.io/badge/React%20Native-20232A?logo=react&logoColor=61DAFB)
![Expo](https://img.shields.io/badge/Expo-000020?logo=expo&logoColor=white)

**IoT & materiel**

![ESP32](https://img.shields.io/badge/ESP32-E7352C?logo=espressif&logoColor=white)
![Arduino](https://img.shields.io/badge/Arduino-00979D?logo=arduino&logoColor=white)
![Raspberry Pi 4](https://img.shields.io/badge/Raspberry%20Pi%204-A22846?logo=raspberrypi&logoColor=white)
![ZMPT101B](https://img.shields.io/badge/ZMPT101B-capteur%20tension-6E4C9F)
![ZMCT103C](https://img.shields.io/badge/ZMCT103C-capteur%20courant-2E7D32)
![Relais](https://img.shields.io/badge/Relais-3%20lignes-455A64)

**Deploiement & infra**

![Vercel](https://img.shields.io/badge/Vercel-000000?logo=vercel&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?logo=railway&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E599?logo=neon&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white)

## Stack

| Couche | Technologies |
| --- | --- |
| Backend | Django REST Framework, PostgreSQL, SimpleJWT, paho-mqtt, scikit-learn/joblib, TensorFlow/Keras, drf-spectacular |
| Frontend | React 18, Vite, Tailwind, React Router, TanStack Query, Zustand, Recharts, Lucide |
| Mobile | React Native Expo, React Navigation, Zustand, AsyncStorage, Expo Notifications |
| Edge | Python, paho-mqtt, httpx, SQLite, FastAPI |
| Infra | Docker, Docker Compose, Nginx, Mosquitto, Vercel (web), Railway (backend), Neon (PostgreSQL) |

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

`House` represente le micro-reseau logique. Les panneaux PV, batteries, onduleurs et autres composants physiques sont dans `EnergyAsset`. Le forecasting n'entraine pas de modele depuis la plateforme : il importe des modeles pre-entraines (GRU consommation, Random Forest production). En l'absence de modele actif, aucune valeur de repli n'est fabriquee : une erreur explicite (503) est renvoyee.

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
- `docs/SYSTEME_EXPERT.md` — le systeme expert flou (source unique)
- `docs/PROTOCOLE_ESP32.md` — protocole des noeuds IoT
- `docs/deployment.md`
- `docs/development-roadmap.md`

## Deploiement (production)

| Service | Plateforme | URL |
| --- | --- | --- |
| Application web | Vercel | https://energyms.vercel.app |
| Backend / API | Railway (`energy_backend`) | https://energy-backend.up.railway.app/api |
| Documentation API (Swagger) | Railway | https://energy-backend.up.railway.app/api/docs/ |
| Admin Django | Railway | https://energy-backend.up.railway.app/admin/ |
| Base de donnees | Neon (PostgreSQL) | https://neon.tech |

> L'application web (Vercel) consomme l'API du backend (Railway), qui persiste sur la
> base PostgreSQL managee (Neon). Configurer `VITE_API_BASE_URL` cote Vercel sur
> `https://energy-backend.up.railway.app/api`, et `DATABASE_URL` cote Railway sur la
> chaine de connexion Neon.

## URLs utiles (developpement local)

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api |
| Swagger | http://localhost:8000/api/docs/ |
| Admin Django | http://localhost:8000/admin/ |
| Edge API | http://localhost:8001/health |
