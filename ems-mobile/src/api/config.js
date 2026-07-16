import { storage } from "../storage";

const CLOUD =
  // process.env.EXPO_PUBLIC_API_BASE_URL || "http://172.20.10.14:8000/api";
  // process.env.EXPO_PUBLIC_API_BASE_URL || "http://192.168.203.117:8000/api";
  process.env.EXPO_PUBLIC_API_BASE_URL || "http://192.168.188.117:8000/api";

const EDGE =
  // process.env.EXPO_PUBLIC_EDGE_API_URL || "http://172.20.10.14:8000/api";
  // process.env.EXPO_PUBLIC_EDGE_API_URL || "http://192.168.203.117:8000/api";
  process.env.EXPO_PUBLIC_EDGE_API_URL || "http://192.168.188.117:8000/api";
  

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
