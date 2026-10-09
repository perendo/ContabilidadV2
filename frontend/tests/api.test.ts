import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "@/lib/api";

describe("Frontend API Client - Hardening Anti-CSRF", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("añade cabecera X-Requested-With: XMLHttpRequest en peticiones mutacionales (POST)", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ access_token: "fake", expires_in: 3600 }),
    } as Response);

    await api.login("admin", "password123");

    expect(fetchSpy).toHaveBeenCalled();
    const calls = fetchSpy.mock.calls[0];
    const options = calls[1] as RequestInit;
    const headers = options.headers as Record<string, string>;

    expect(headers["X-Requested-With"]).toBe("XMLHttpRequest");
  });

  it("no añade obligatoriamente X-Requested-With en peticiones de lectura (GET)", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify([]),
    } as Response);

    await api.empresas();

    expect(fetchSpy).toHaveBeenCalled();
    const calls = fetchSpy.mock.calls[0];
    const options = calls[1] as RequestInit;
    const headers = (options?.headers as Record<string, string>) || {};

    expect(headers["X-Requested-With"]).toBeUndefined();
  });
});
