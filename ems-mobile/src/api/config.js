import { storage } from "../storage";

// Adresse LAN du PC hébergeant le backend. Sur mobile, JAMAIS "localhost" :
// depuis le téléphone, localhost désigne le téléphone lui-même, pas le PC.
// Aucune détection automatique fiable côté mobile — on passe donc par
// EXPO_PUBLIC_API_BASE_URL (fichier .env), avec ce repli en dur.
// Pour retrouver l'adresse courante : python scripts/configure_lan.py
const LAN_API_FALLBACK = "http://192.168.0.117:8000/api";

const CLOUD = process.env.EXPO_PUBLIC_API_BASE_URL || LAN_API_FALLBACK;
const EDGE = process.env.EXPO_PUBLIC_EDGE_API_URL || LAN_API_FALLBACK;
  

/**
 * Resolve the active API base URL according to the user's selected mode:
 *   - cloud : remote API (default)
 *   - edge  : local Raspberry Pi / Edge Gateway on the LAN
 *   - local : a custom URL entered by the user (dev / specific IP)
 */
export async function resolveBaseUrl() {
  const mode = await storage.getApiMode();
  if (mode === "edge") return EDGE;
  if (mode === "local") {
    const custom = await storage.getCustomUrl();
    return custom || CLOUD;
  }
  return CLOUD;
}

export const API_PRESETS = { cloud: CLOUD, edge: EDGE };
