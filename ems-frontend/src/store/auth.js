import { create } from "zustand";
import { authApi } from "../api/endpoints";
import { TOKEN_KEY } from "../api/client";

export const useAuthStore = create((set) => ({
  user: null,
  loading: true,
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),

  async bootstrap() {
    if (!localStorage.getItem(TOKEN_KEY)) {
      set({ loading: false, isAuthenticated: false });
      return;
    }
    try {
      const user = await authApi.me();
      set({ user, isAuthenticated: true, loading: false });
    } catch {
      set({ user: null, isAuthenticated: false, loading: false });
    }
  },

  async login(username, password) {
    await authApi.login(username, password);
    const user = await authApi.me();
    set({ user, isAuthenticated: true, loading: false });
    return user;
  },

  async updateUser(payload) {
    const user = await authApi.updateMe(payload);
    set({ user });
    return user;
  },

  logout() {
    authApi.logout();
    set({ user: null, isAuthenticated: false });
  },
}));
