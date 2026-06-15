import axios from "axios";
import { storage } from "../storage";
import { resolveBaseUrl } from "./config";

export const api = axios.create();

// Inject the resolved base URL + JWT before each request.
api.interceptors.request.use(async (config) => {
  config.baseURL = await resolveBaseUrl();
  const token = await storage.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/**
 * GET helper with offline cache fallback:
 * returns fresh data when online, otherwise the last cached payload.
 */
export async function getWithCache(path, params, cacheKey) {
  try {
    const { data } = await api.get(path, { params });
    if (cacheKey) await storage.cacheSet(cacheKey, data);
    return { data, fromCache: false };
  } catch (err) {
    if (cacheKey) {
      const cached = await storage.cacheGet(cacheKey);
      if (cached) return { data: cached, fromCache: true };
    }
    throw err;
  }
}
