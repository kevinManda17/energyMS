import { api, TOKEN_KEY, REFRESH_KEY } from "./client";

// ---- Auth -----------------------------------------------------------------
export const authApi = {
  async login(username, password) {
    const { data } = await api.post("/auth/login/", { username, password });
    localStorage.setItem(TOKEN_KEY, data.access);
    localStorage.setItem(REFRESH_KEY, data.refresh);
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
  logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// ---- Domain resources -----------------------------------------------------
export const housesApi = {
  list: () => api.get("/houses/").then((r) => r.data),
  create: (p) => api.post("/houses/", p).then((r) => r.data),
  update: (id, p) => api.put(`/houses/${id}/`, p).then((r) => r.data),
  patch: (id, p) => api.patch(`/houses/${id}/`, p).then((r) => r.data),
  remove: (id) => api.delete(`/houses/${id}/`),
};

export const devicesApi = {
  sensors: (houseId) =>
    api.get(`/houses/${houseId}/sensors/`).then((r) => r.data),
  createSensor: (houseId, p) =>
    api.post(`/houses/${houseId}/sensors/`, p).then((r) => r.data),
  equipment: (houseId) =>
    api.get(`/houses/${houseId}/equipment/`).then((r) => r.data),
  createEquipment: (houseId, p) =>
    api.post(`/houses/${houseId}/equipment/`, p).then((r) => r.data),
  updateEquipment: (id, p) =>
    api.put(`/equipment/${id}/`, p).then((r) => r.data),
  removeEquipment: (id) => api.delete(`/equipment/${id}/`),
};

// ---- Commande des relais (3 lignes du prototype) --------------------------
export const relaysApi = {
  get: (houseId) => api.get(`/houses/${houseId}/relays/`).then((r) => r.data),
  set: (houseId, patch) =>
    api.patch(`/houses/${houseId}/relays/`, patch).then((r) => r.data),
};

export const measurementsApi = {
  list: (params) => api.get("/measurements/", { params }).then((r) => r.data),
  latest: (houseId) =>
    api.get("/measurements/latest/", { params: { house: houseId } }).then((r) => r.data),
  history: (params) =>
    api.get("/measurements/history/", { params }).then((r) => r.data),
};

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
  predict: (params) =>
    api.get("/forecasting/predict/", { params }).then((r) => r.data),
  predictions: (params) =>
    api.get("/forecasting/predictions/", { params }).then((r) => r.data),
  models: () => api.get("/forecasting/models/").then((r) => r.data),
  updateModel: (id, p) =>
    api.patch(`/forecasting/models/${id}/`, p).then((r) => r.data),
};

export const decisionsApi = {
  list: (params) => api.get("/decisions/", { params }).then((r) => r.data),
  latest: () => api.get("/decisions/latest/").then((r) => r.data),
  detail: (id) => api.get(`/decisions/${id}/`).then((r) => r.data),
  trigger: (p) => api.post("/decisions/trigger/", p).then((r) => r.data),
};

export const alertsApi = {
  list: (params) => api.get("/alerts/", { params }).then((r) => r.data),
  unread: () => api.get("/alerts/unread/").then((r) => r.data),
  acknowledge: (id) => api.post(`/alerts/${id}/acknowledge/`).then((r) => r.data),
};

export const reportsApi = {
  daily: (params) => api.get("/reports/daily/", { params }).then((r) => r.data),
  exportCsvUrl: () =>
    `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"}/reports/export/csv/`,
};

export const datasetsApi = {
  list: () => api.get("/datasets/").then((r) => r.data),
  import: (formData) =>
    api.post("/datasets/import/", formData).then((r) => r.data),
};
