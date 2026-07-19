import axios from "axios";
import { API_BASE_URL } from "./baseUrl";

// Résolue une seule fois, dans src/api/baseUrl.js (VITE_API_BASE_URL, puis
// repli sur l'hôte courant). Ne jamais coder d'adresse en dur ici.
const BASE_URL = API_BASE_URL;

export const TOKEN_KEY = "ems_access";
export const REFRESH_KEY = "ems_refresh";

export const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Transparent refresh on 401.
let refreshing = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      const refresh = localStorage.getItem(REFRESH_KEY);
      if (!refresh) return Promise.reject(error);
      original._retry = true;
      try {
        refreshing =
          refreshing ||
          axios.post(`${BASE_URL}/auth/refresh/`, { refresh });
        const { data } = await refreshing;
        refreshing = null;
        localStorage.setItem(TOKEN_KEY, data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch (e) {
        refreshing = null;
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        window.location.href = "/login";
        return Promise.reject(e);
      }
    }
    return Promise.reject(error);
  }
);
