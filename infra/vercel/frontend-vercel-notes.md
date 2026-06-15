# Frontend React sur Vercel

1. **Import** du repo dans Vercel.
2. **Root Directory** : `ems-frontend`.
3. **Framework Preset** : Vite (détecté automatiquement).
   - Build Command : `npm run build`
   - Output Directory : `dist`
4. **Environment Variables** :
   | Clé | Valeur |
   |-----|--------|
   | `VITE_API_BASE_URL` | `https://api.votre-domaine.com/api` |
   | `VITE_APP_NAME` | `EMS Dashboard` |
5. Le fichier `vercel.json` assure le **fallback SPA** (toutes les routes → `index.html`).
6. Après déploiement, ajouter l'URL Vercel à `CORS_ALLOWED_ORIGINS` du backend AWS.

> Premier test rapide : déployer le frontend sur Vercel en pointant
> `VITE_API_BASE_URL` vers le backend (EC2/ECS) une fois celui-ci en ligne.
