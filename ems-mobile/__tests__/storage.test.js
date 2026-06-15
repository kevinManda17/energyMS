/**
 * Tests for token storage and cloud/edge/local API mode selection.
 * AsyncStorage is mocked with a simple in-memory map.
 */
jest.mock("@react-native-async-storage/async-storage", () => {
  let store = {};
  return {
    setItem: jest.fn((k, v) => {
      store[k] = v;
      return Promise.resolve();
    }),
    getItem: jest.fn((k) => Promise.resolve(store[k] ?? null)),
    multiSet: jest.fn((pairs) => {
      pairs.forEach(([k, v]) => (store[k] = v));
      return Promise.resolve();
    }),
    multiRemove: jest.fn((keys) => {
      keys.forEach((k) => delete store[k]);
      return Promise.resolve();
    }),
  };
});

import { storage } from "../src/storage";

describe("token storage", () => {
  it("stores and clears tokens", async () => {
    await storage.setTokens("access1", "refresh1");
    expect(await storage.getToken()).toBe("access1");
    await storage.clearTokens();
    expect(await storage.getToken()).toBeNull();
  });
});

describe("API mode", () => {
  it("defaults to cloud", async () => {
    expect(await storage.getApiMode()).toBe("cloud");
  });
  it("switches to edge", async () => {
    await storage.setApiMode("edge");
    expect(await storage.getApiMode()).toBe("edge");
  });
  it("stores a custom local url", async () => {
    await storage.setCustomUrl("http://192.168.1.50:8000/api");
    expect(await storage.getCustomUrl()).toBe("http://192.168.1.50:8000/api");
  });
});
