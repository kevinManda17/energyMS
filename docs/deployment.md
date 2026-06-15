# Déploiement

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

## 2. Frontend React sur Vercel
1. Importer le repo, **Root Directory = `ems-frontend`**.
2. Framework preset : Vite. Build : `npm run build`, output `dist`.
3. Variable d'env : `VITE_API_BASE_URL=https://api.votre-domaine.com/api`.
4. `vercel.json` gère déjà le fallback SPA.

## 3. Expo Web sur Vercel (optionnel)
- `cd ems-mobile && npx expo export --platform web` → dossier `dist`.
- Déployer `dist` sur Vercel (projet séparé). Voir `infra/vercel/expo-web-vercel-notes.md`.

## 4. Backend sur AWS
Voir `infra/aws/` :
- `rds-postgresql-notes.md` — base managée.
- `ec2-deployment-notes.md` — Docker Compose sur EC2.
- `ecs-deployment-notes.md` — conteneurs sur ECS Fargate.
- `s3-cloudfront-notes.md` — assets statiques.

## 5. Variables d'environnement
Voir `docs/environment-variables.md` et `.env.example` (racine = prod compose).

## 6. HTTP → HTTPS
- En local/EC2 : Nginx (`nginx/default.conf`) + certificat (Let's Encrypt / certbot).
- Sur ECS/ALB : terminaison TLS au niveau du Load Balancer (ACM).
- `config/settings/production.py` active déjà HSTS et cookies sécurisés.

## 7. CORS Vercel ↔ AWS
Définir `CORS_ALLOWED_ORIGINS=https://votre-frontend.vercel.app` côté backend.
