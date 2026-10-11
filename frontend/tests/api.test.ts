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

  it("todasLasCuentas pagina con limit=200 y agrega todos los items", async () => {
    const cuenta = (id: number) => ({
      id,
      ejercicio_id: 1,
      codigo: String(id),
      nombre: `Cuenta ${id}`,
      nivel: 3,
    });
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({ total: 3, offset: 0, limit: 200, items: [cuenta(1), cuenta(2)] }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({ total: 3, offset: 2, limit: 200, items: [cuenta(3)] }),
      } as Response);

    const res = await api.todasLasCuentas();

    expect(res.map((c) => c.id)).toEqual([1, 2, 3]);
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    const urls = fetchSpy.mock.calls.map((c) => String(c[0]));
    expect(urls.every((u) => u.includes("limit=200"))).toBe(true);
    expect(urls.some((u) => u.includes("limit=500"))).toBe(false);
  });
});
