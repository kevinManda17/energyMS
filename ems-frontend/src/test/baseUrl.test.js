import { describe, it, expect } from "vitest";
import { resolveApiBaseUrl } from "../api/baseUrl";

describe("resolveApiBaseUrl", () => {
  it("utilise VITE_API_BASE_URL quand elle est definie", () => {
    const url = resolveApiBaseUrl(
      { VITE_API_BASE_URL: "http://192.168.84.117:8000/api" },
      { hostname: "autre-hote", protocol: "http:" }
    );
    expect(url).toBe("http://192.168.84.117:8000/api");
  });

  it("supprime le slash final de la variable d'environnement", () => {
    const url = resolveApiBaseUrl(
      { VITE_API_BASE_URL: "http://192.168.84.117:8000/api/" },
      {}
    );
    expect(url).toBe("http://192.168.84.117:8000/api");
  });

  it("retombe sur l'hote de la page quand la variable est absente", () => {
    const url = resolveApiBaseUrl({}, { hostname: "192.168.84.117", protocol: "http:" });
    expect(url).toBe("http://192.168.84.117:8000/api");
  });

  it("suit l'hote courant, quel que soit le reseau", () => {
    const url = resolveApiBaseUrl({}, { hostname: "10.20.30.40", protocol: "http:" });
    expect(url).toBe("http://10.20.30.40:8000/api");
  });

  it("conserve https quand la page est servie en https", () => {
    const url = resolveApiBaseUrl({}, { hostname: "ems.example.com", protocol: "https:" });
    expect(url).toBe("https://ems.example.com:8000/api");
  });

  it("suit localhost quand la page elle-meme est sur localhost (dev local)", () => {
    // Comportement voulu : sur la machine de dev, l'API est aussi en local.
    const url = resolveApiBaseUrl({}, { hostname: "localhost", protocol: "http:" });
    expect(url).toBe("http://localhost:8000/api");
  });

  it("hors navigateur, retombe sur l'adresse LAN et jamais sur localhost", () => {
    // `null` (et non `undefined`) pour ne pas declencher la valeur par defaut.
    const url = resolveApiBaseUrl({}, null);
    expect(url).not.toContain("localhost");
    expect(url).not.toContain("127.0.0.1");
    expect(url).toMatch(/^http:\/\/\d+\.\d+\.\d+\.\d+:8000\/api$/);
  });
});
