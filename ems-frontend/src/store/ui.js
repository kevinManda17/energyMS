import { create } from "zustand";

const storedTheme = localStorage.getItem("ems_theme") || "light";
const storedHouse = Number(localStorage.getItem("ems_house")) || null;

function applyTheme(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}
applyTheme(storedTheme);

export const useUIStore = create((set, get) => ({
  theme: storedTheme,
  sidebarOpen: false,
  currentHouseId: storedHouse,

  toggleTheme() {
    const theme = get().theme === "dark" ? "light" : "dark";
    localStorage.setItem("ems_theme", theme);
    applyTheme(theme);
    set({ theme });
  },
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  closeSidebar: () => set({ sidebarOpen: false }),
  setHouse(id) {
    localStorage.setItem("ems_house", String(id));
    set({ currentHouseId: id });
  },
}));
