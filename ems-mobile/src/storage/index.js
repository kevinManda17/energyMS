import AsyncStorage from "@react-native-async-storage/async-storage";

const KEYS = {
  TOKEN: "ems_token",
  REFRESH: "ems_refresh",
  API_MODE: "ems_api_mode", // cloud | edge | local
  API_CUSTOM: "ems_api_custom",
  HOUSE_ID: "ems_house_id",
  THEME: "ems_theme",       // light | dark | system
  CACHE: "ems_cache_",
};

export const storage = {
  // --- auth tokens ---
  async setTokens(access, refresh) {
    await AsyncStorage.multiSet([
      [KEYS.TOKEN, access],
      [KEYS.REFRESH, refresh || ""],
    ]);
  },
  getToken: () => AsyncStorage.getItem(KEYS.TOKEN),
  getRefresh: () => AsyncStorage.getItem(KEYS.REFRESH),
  async clearTokens() {
    await AsyncStorage.multiRemove([KEYS.TOKEN, KEYS.REFRESH]);
  },

  // --- API mode (cloud / edge / local custom) ---
  getApiMode: async () => (await AsyncStorage.getItem(KEYS.API_MODE)) || "cloud",
  setApiMode: (mode) => AsyncStorage.setItem(KEYS.API_MODE, mode),
  getCustomUrl: () => AsyncStorage.getItem(KEYS.API_CUSTOM),
  setCustomUrl: (url) => AsyncStorage.setItem(KEYS.API_CUSTOM, url),

  // --- app theme preference ---
  getTheme: async () => (await AsyncStorage.getItem(KEYS.THEME)) || "system",
  setTheme: (theme) => AsyncStorage.setItem(KEYS.THEME, theme),

  getHouseId: async () => {
    const value = await AsyncStorage.getItem(KEYS.HOUSE_ID);
    return value ? Number(value) : null;
  },
  setHouseId: (id) => AsyncStorage.setItem(KEYS.HOUSE_ID, String(id)),

  // --- offline cache ---
  async cacheSet(key, data) {
    await AsyncStorage.setItem(KEYS.CACHE + key, JSON.stringify(data));
  },
  async cacheGet(key) {
    const raw = await AsyncStorage.getItem(KEYS.CACHE + key);
    return raw ? JSON.parse(raw) : null;
  },
};
