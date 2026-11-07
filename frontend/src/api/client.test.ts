import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError, api, getAccessToken, onSessionEnded, setSession } from "./client";

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

const expired = () => json(401, { error: { code: "invalid_token", message: "Token inválido" } });
const renewed = () => json(200, { access_token: "nuevo", refresh_token: "r2" });

describe("api", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    setSession({ access_token: "viejo", refresh_token: "r1" });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setSession(null);
  });

  const urls = () => fetchMock.mock.calls.map((c) => c[0] as string);

  test("añade el token de acceso", async () => {
    fetchMock.mockResolvedValueOnce(json(200, { ok: true }));
    await api("/api/songs");
    const headers = new Headers(fetchMock.mock.calls[0][1].headers);
    expect(headers.get("authorization")).toBe("Bearer viejo");
  });

  test("renueva el token una sola vez ante 401 y reintenta", async () => {
    fetchMock.mockResolvedValueOnce(expired()).mockResolvedValueOnce(renewed()).mockResolvedValueOnce(json(200, { ok: 1 }));
    await expect(api("/api/songs")).resolves.toEqual({ ok: 1 });
    expect(urls()).toEqual(["/api/songs", "/api/auth/refresh", "/api/songs"]);
    expect(getAccessToken()).toBe("nuevo");
  });

  test("no reintenta más de una vez", async () => {
    fetchMock.mockResolvedValueOnce(expired()).mockResolvedValueOnce(renewed()).mockResolvedValueOnce(expired());
    await expect(api("/api/songs")).rejects.toMatchObject({ status: 401 });
    expect(urls()).toHaveLength(3);
  });

  test("si el refresh falla, cierra sesión y lanza ApiError", async () => {
    const ended = vi.fn();
    const stop = onSessionEnded(ended);
    fetchMock.mockResolvedValueOnce(expired()).mockResolvedValueOnce(expired());
    await expect(api("/api/songs")).rejects.toBeInstanceOf(ApiError);
    expect(ended).toHaveBeenCalledOnce();
    expect(getAccessToken()).toBeNull();
    stop();
  });

  test("dos 401 simultáneos comparten un solo refresh", async () => {
    fetchMock.mockImplementation(async (url: string, init: RequestInit) => {
      if (url === "/api/auth/refresh") return renewed();
      const token = new Headers(init.headers).get("authorization");
      return token === "Bearer nuevo" ? json(200, { ok: 1 }) : expired();
    });
    await Promise.all([api("/api/a"), api("/api/b")]);
    expect(urls().filter((u) => u === "/api/auth/refresh")).toHaveLength(1);
  });

  test("traduce el error uniforme del backend", async () => {
    fetchMock.mockResolvedValueOnce(json(409, { error: { code: "tape_full", message: "El casete ya está lleno" } }));
    await expect(api("/api/tapes/1/tracks", { method: "POST", json: {} })).rejects.toMatchObject({
      status: 409,
      code: "tape_full",
      message: "El casete ya está lleno",
    });
  });

  test("un error de red se vuelve ApiError legible", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("failed"));
    await expect(api("/api/songs")).rejects.toMatchObject({ status: 0, code: "network_error" });
  });

  test("204 devuelve undefined", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(api("/api/x", { method: "DELETE" })).resolves.toBeUndefined();
  });

  test("manda JSON con encabezado", async () => {
    fetchMock.mockResolvedValueOnce(json(200, {}));
    await api("/api/x", { method: "POST", json: { a: 1 } });
    const init = fetchMock.mock.calls[0][1];
    expect(new Headers(init.headers).get("content-type")).toBe("application/json");
    expect(init.body).toBe('{"a":1}');
  });

  describe("al renovar", () => {
    const refreshBody = (index: number) =>
      JSON.parse(fetchMock.mock.calls.filter((c) => c[0] === "/api/auth/refresh")[index][1].body as string);

    test("un corte de red conserva la sesión", async () => {
      const ended = vi.fn();
      const stop = onSessionEnded(ended);
      fetchMock.mockImplementation(async (url: string) => {
        if (url === "/api/auth/refresh") throw new TypeError("connection reset");
        return expired();
      });
      await expect(api("/api/notices")).rejects.toMatchObject({ status: 0, code: "network_error" });
      expect(localStorage.getItem("meloxo.refresh")).toBe("r1");
      expect(getAccessToken()).toBe("viejo");
      expect(ended).not.toHaveBeenCalled();
      stop();
    });

    test("un error del servidor conserva la sesión", async () => {
      const ended = vi.fn();
      const stop = onSessionEnded(ended);
      fetchMock.mockImplementation(async (url: string) => (url === "/api/auth/refresh" ? json(503, {}) : expired()));
      await expect(api("/api/notices")).rejects.toMatchObject({ status: 0 });
      expect(localStorage.getItem("meloxo.refresh")).toBe("r1");
      expect(ended).not.toHaveBeenCalled();
      stop();
    });

    test("si otra pestaña ganó la renovación, sigue con su token", async () => {
      let attempts = 0;
      fetchMock.mockImplementation(async (url: string) => {
        if (url === "/api/auth/refresh") {
          attempts += 1;
          if (attempts === 1) {
            localStorage.setItem("meloxo.refresh", "de-la-otra-pestana");
            return expired();
          }
          return renewed();
        }
        return attempts === 2 ? json(200, { ok: true }) : expired();
      });
      await expect(api("/api/notices")).resolves.toEqual({ ok: true });
      expect(refreshBody(1).refresh_token).toBe("de-la-otra-pestana");
      expect(localStorage.getItem("meloxo.refresh")).toBe("r2");
    });

    test("dos pestañas renuevan por turnos con un candado", async () => {
      const request = vi.fn((_name: string, work: () => Promise<unknown>) => work());
      vi.stubGlobal("navigator", { ...navigator, locks: { request } });
      fetchMock.mockResolvedValueOnce(expired()).mockResolvedValueOnce(renewed()).mockResolvedValueOnce(json(200, {}));
      await api("/api/notices");
      expect(request).toHaveBeenCalledWith("meloxo.refresh", expect.any(Function));
    });
  });
});
