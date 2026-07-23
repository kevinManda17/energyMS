/**
 * Résolution de l'URL de l'API — source unique pour tout le frontend.
 *
 * Ordre de priorité :
 *   1. VITE_API_BASE_URL (fichier .env) — c'est la voie recommandée ;
 *   2. repli dynamique : même hôte que la page, port 8000. Utile quand on ouvre
 *      le tableau de bord depuis un autre appareil du réseau : la page servie
 *      par http://192.168.0.117:5173 appellera http://192.168.0.117:8000/api,
 *      sans rien reconfigurer ;
 *   3. repli statique (hors navigateur : tests, SSR).
 *
 * Le repli n°2 n'est correct que si le backend tourne sur la MÊME machine que
 * le serveur frontend. Si les deux sont séparés, définir VITE_API_BASE_URL.
 *
 * On n'écrit jamais « localhost » en dur : depuis un téléphone, localhost
 * désigne le téléphone, pas le PC qui héberge l'API.
 */
export const BACKEND_PORT = 8000;

// Repli utilisé uniquement hors navigateur (tests unitaires, rendu serveur).
const STATIC_FALLBACK_HOST = "192.168.0.117";

export function resolveApiBaseUrl(env = import.meta.env, loc = globalThis.location) {
  const configured = env?.VITE_API_BASE_URL;
  if (configured) return String(configured).trim().replace(/\/+$/, "");

  const hostname = loc?.hostname;
  if (hostname) {
    const protocol = loc.protocol === "https:" ? "https:" : "http:";
    return `${protocol}//${hostname}:${BACKEND_PORT}/api`;
  }

  return `http://${STATIC_FALLBACK_HOST}:${BACKEND_PORT}/api`;
}

export const API_BASE_URL = resolveApiBaseUrl();
