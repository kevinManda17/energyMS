import { api, getWithCache } from "./client";
import { storage } from "../storage";
import { resolveBaseUrl } from "./config";

export const authApi = {
  async login(username, password) {
    const { data } = await api.post("/auth/login/", { username, password });
    await storage.setTokens(data.access, data.refresh);
    return data;
  },
  register: (payload) => api.post("/auth/register/", payload).then((r) => r.data),
  sendPhoneCode: (payload) =>
    api.post("/auth/phone/send-code/", payload).then((r) => r.data),
  verifyPhoneCode: (payload) =>
    api.post("/auth/phone/verify-code/", payload).then((r) => r.data),
  me: () => api.get("/auth/me/").then((r) => r.data),
  updateMe: (payload) => api.patch("/auth/me/", payload).then((r) => r.data),
  changePassword: (payload) =>
    api.post("/auth/password/change/", payload).then((r) => r.data),
  logout: () => storage.clearTokens(),
};

export const housesApi = {
  list: () => getWithCache("/houses/", null, "houses"),
  create: (payload) => api.post("/houses/", payload).then((r) => r.data),
  update: (id, payload) => api.put(`/houses/${id}/`, payload).then((r) => r.data),
  patch: (id, payload) => api.patch(`/houses/${id}/`, payload).then((r) => r.data),
};

export const devicesApi = {
  sensors: (houseId) => getWithCache(`/houses/${houseId}/sensors/`, null, `sensors_${houseId}`),
  equipment: (houseId) => getWithCache(`/houses/${houseId}/equipment/`, null, `equipment_${houseId}`),
  createEquipment: (houseId, payload) =>
    api.post(`/houses/${houseId}/equipment/`, payload).then((r) => r.data),
  updateEquipment: (id, payload) => api.put(`/equipment/${id}/`, payload).then((r) => r.data),
  removeEquipment: (id) => api.delete(`/equipment/${id}/`),
};

// Commande des relais (3 lignes du prototype) : toujours en direct.
export const relaysApi = {
  get: (houseId) => api.get(`/houses/${houseId}/relays/`).then((r) => r.data),
  set: (houseId, patch) =>
    api.patch(`/houses/${houseId}/relays/`, patch).then((r) => r.data),
};

export const measurementsApi = {
  latest: (houseId) => getWithCache("/measurements/latest/", { house: houseId }, `latest_${houseId || "all"}`),
  history: (params) => getWithCache("/measurements/history/", params, `history_${JSON.stringify(params || {})}`),
};

// Collecte météo Open-Meteo : toujours en direct (pas de cache) — le statut
// sert à afficher la fraîcheur des données, il doit être exact.
export const weatherApi = {
  collect: (houseId) =>
    api
      .post("/measurements/weather/collect/", houseId ? { house: houseId } : {})
      .then((r) => r.data),
  status: (houseId) =>
    api
      .get("/measurements/weather/status/", { params: houseId ? { house: houseId } : {} })
      .then((r) => r.data),
};

export const forecastingApi = {
  predict: (params) => api.get("/forecasting/predict/", { params }).then((r) => r.data),
  predictions: (params) => getWithCache("/forecasting/predictions/", params, "predictions"),
  models: () => getWithCache("/forecasting/models/", null, "forecast_models"),
};

export const decisionsApi = {
  list: (params) => getWithCache("/decisions/", params, "decisions"),
  latest: () => getWithCache("/decisions/latest/", null, "decision_latest"),
  detail: (id) => api.get(`/decisions/${id}/`).then((r) => r.data),
  trigger: (payload) => api.post("/decisions/trigger/", payload).then((r) => r.data),
};

export const alertsApi = {
  list: (params) => getWithCache("/alerts/", params || { page_size: 50 }, "alerts"),
  acknowledge: (id) => api.post(`/alerts/${id}/acknowledge/`).then((r) => r.data),
};

export const reportsApi = {
  daily: (params) => getWithCache("/reports/daily/", params, "report_daily"),
  summary: (params) =>
    getWithCache(
      "/reports/summary/",
      params,
      `report_summary_${params?.house || "all"}_${params?.days || "7"}`
    ),
  async exportCsvUrl() {
    const base = await resolveBaseUrl();
    return `${base}/reports/export/csv/`;
  },
};

export const dataApi = {
  latest: measurementsApi.latest,
  history: measurementsApi.history,
  decisionLatest: decisionsApi.latest,
  alerts: alertsApi.list,
  acknowledge: alertsApi.acknowledge,
};
