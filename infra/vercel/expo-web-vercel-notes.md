# Expo Web sur Vercel (optionnel)

L'app mobile Expo peut aussi être exportée en web et déployée sur Vercel.

1. Export web :
   ```bash
   cd ems-mobile
   npx expo export --platform web   # génère ./dist
   ```
2. Sur Vercel : nouveau projet, **Root Directory = `ems-mobile`**.
   - Build Command : `npx expo export --platform web`
   - Output Directory : `dist`
3. Variables d'env :
   - `EXPO_PUBLIC_API_BASE_URL=https://api.votre-domaine.com/api`
4. CORS : ajouter l'URL au backend.

> Optionnel : la cible principale du mobile reste iOS/Android via EAS Build.
> L'export web sert surtout aux démonstrations rapides.
