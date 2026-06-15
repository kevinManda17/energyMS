import { api, getWithCache } from "./client";
import { storage } from "../storage";

export const authApi = {
  async login(username, password) {
    const { data } = await api.post("/auth/login/", { username, password });
    await storage.setTokens(data.access, data.refresh);
    return data;
  },
  register: (payload) => api.post("/auth/register/", payload).then((r) => r.data),
  me: () => api.get("/auth/me/").then((r) => r.data),
  logout: () => storage.clearTokens(),
};

export const dataApi = {
  latest: (houseId) =>
    getWithCache("/measurements/latest/", { house: houseId }, `latest_${houseId}`),
  history: (params) =>
    getWithCache("/measurements/history/", params, "history"),
  decisionLatest: () =>
    getWithCache("/decisions/latest/", null, "decision_latest"),
  alerts: () => getWithCache("/alerts/", { page_size: 50 }, "alerts"),
  acknowledge: (id) => api.post(`/alerts/${id}/acknowledge/`).then((r) => r.data),
};
