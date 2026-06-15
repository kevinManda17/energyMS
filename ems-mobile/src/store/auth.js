import { create } from "zustand";
import { authApi } from "../api/endpoints";
import { storage } from "../storage";

export const useAuthStore = create((set) => ({
  user: null,
  ready: false,
  isAuthenticated: false,

  async bootstrap() {
    const token = await storage.getToken();
    if (!token) {
      set({ ready: true, isAuthenticated: false });
      return;
    }
    try {
      const user = await authApi.me();
      set({ user, isAuthenticated: true, ready: true });
    } catch {
      set({ isAuthenticated: false, ready: true });
    }
  },

  async login(username, password) {
    await authApi.login(username, password);
    const user = await authApi.me();
    set({ user, isAuthenticated: true });
  },

  async logout() {
    await authApi.logout();
    set({ user: null, isAuthenticated: false });
  },
}));
