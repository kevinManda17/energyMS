import { create } from "zustand";
import { storage } from "../storage";

export const useThemeStore = create((set) => ({
  theme: "system", // "light" | "dark" | "system"

  async bootstrap() {
    const saved = await storage.getTheme();
    set({ theme: saved || "system" });
  },

  async setTheme(theme) {
    await storage.setTheme(theme);
    set({ theme });
  },
}));
