# Deploiement

## 1. Local avec Docker

```bash
cd ems-platform
docker compose up --build           # db, mqtt, backend, frontend, mqtt_worker
docker compose --profile edge up    # + edge-gateway
```

- Frontend : http://localhost:5173
- API : http://localhost:8000/api
- Swagger : http://localhost:8000/api/docs/
- Le service `backend` lance automatiquement `migrate` + `seed_initial_data`.
- Le seed cree maintenant les micro-reseaux, actifs energetiques, capteurs, equipements, mesures, previsions, decisions et alertes.

## 2. Migrations importantes

Les migrations recentes deplacent les anciennes capacites PV/batterie de `House` vers `EnergyAsset`, puis renomment les previsions vers `ImportedModel` et `Forecast`.

```bash
cd ems-backend
python manage.py migrate
python manage.py seed_initial_data
```

## 3. Frontend React sur Vercel

1. Importer le repo, **Root Directory = `ems-frontend`**.
2. Framework preset : Vite. Build : `npm run build`, output `dist`.
3. Variable d'env : `VITE_API_BASE_URL=https://api.votre-domaine.com/api`.
4. `vercel.json` gere deja le fallback SPA.

## 4. Expo Web sur Vercel (optionnel)

- `cd ems-mobile && npx expo export --platform web` -> dossier `dist`.
- Deployer `dist` sur Vercel (projet separe). Voir `infra/vercel/expo-web-vercel-notes.md`.

## 5. Backend sur AWS

Voir `infra/aws/` :

- `rds-postgresql-notes.md` : base managee.
- `ec2-deployment-notes.md` : Docker Compose sur EC2.
- `ecs-deployment-notes.md` : conteneurs sur ECS Fargate.
- `s3-cloudfront-notes.md` : assets statiques.

## 6. Variables d'environnement

Voir `docs/environment-variables.md` et `.env.example`.

## 7. HTTP -> HTTPS

- En local/EC2 : Nginx (`nginx/default.conf`) + certificat (Let's Encrypt / certbot).
- Sur ECS/ALB : terminaison TLS au niveau du Load Balancer (ACM).
- `config/settings/production.py` active HSTS et cookies securises.

## 8. CORS Vercel / AWS

Definir `CORS_ALLOWED_ORIGINS=https://votre-frontend.vercel.app` cote backend.
