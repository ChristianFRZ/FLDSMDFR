import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError, hasSession, onSessionEnded } from "../api/client";
import { routes } from "../test-utils";
import { AuthProvider, useAuth } from "./AuthContext";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
  hasSession: vi.fn(() => false),
  setSession: vi.fn(),
  getRefreshToken: vi.fn(() => null),
  onSessionEnded: vi.fn(() => () => undefined),
}));

const me = { id: "u1", email: "ana@correo.mx", display_name: "Ana", role: "listener" };
const tokens = { access_token: "a", refresh_token: "r" };

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(hasSession).mockReturnValue(false);
  vi.mocked(onSessionEnded).mockImplementation(() => () => undefined);
});

test("login correcto activa entered", async () => {
  vi.mocked(api).mockImplementation(routes({ "/api/auth/login": tokens, "/api/users/me": me }) as typeof api);
  const { result } = renderHook(() => useAuth(), { wrapper });
  expect(result.current.entered).toBe(false);
  await act(() => result.current.login("ana@correo.mx", "secreto"));
  expect(result.current.user).toEqual(me);
  expect(result.current.entered).toBe(true);
});

test("login fallido no activa entered", async () => {
  vi.mocked(api).mockImplementation(
    routes({ "/api/auth/login": new ApiError(401, "invalid_credentials", "Credenciales inválidas") }) as typeof api,
  );
  const { result } = renderHook(() => useAuth(), { wrapper });
  await act(() => expect(result.current.login("ana@correo.mx", "mala")).rejects.toThrow());
  expect(result.current.user).toBeNull();
  expect(result.current.entered).toBe(false);
});

test("register correcto activa entered", async () => {
  vi.mocked(api).mockImplementation(routes({ "/api/auth/register": tokens, "/api/users/me": me }) as typeof api);
  const { result } = renderHook(() => useAuth(), { wrapper });
  await act(() => result.current.register("ana@correo.mx", "secreto", "Ana"));
  expect(result.current.entered).toBe(true);
});

test("cargar una sesión guardada no activa entered", async () => {
  vi.mocked(hasSession).mockReturnValue(true);
  vi.mocked(api).mockImplementation(routes({ "/api/users/me": me }) as typeof api);
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.user).toEqual(me);
  expect(result.current.entered).toBe(false);
});

test("clearEntered lo apaga", async () => {
  vi.mocked(api).mockImplementation(routes({ "/api/auth/login": tokens, "/api/users/me": me }) as typeof api);
  const { result } = renderHook(() => useAuth(), { wrapper });
  await act(() => result.current.login("ana@correo.mx", "secreto"));
  act(() => result.current.clearEntered());
  expect(result.current.entered).toBe(false);
});

test("logout apaga entered", async () => {
  vi.mocked(api).mockImplementation(routes({ "/api/auth/login": tokens, "/api/users/me": me }) as typeof api);
  const { result } = renderHook(() => useAuth(), { wrapper });
  await act(() => result.current.login("ana@correo.mx", "secreto"));
  await act(() => result.current.logout());
  expect(result.current.entered).toBe(false);
});

test("el fin de sesión apaga entered", async () => {
  let ended = () => undefined as void;
  vi.mocked(onSessionEnded).mockImplementation((listener) => {
    ended = listener;
    return () => undefined;
  });
  vi.mocked(api).mockImplementation(routes({ "/api/auth/login": tokens, "/api/users/me": me }) as typeof api);
  const { result } = renderHook(() => useAuth(), { wrapper });
  await act(() => result.current.login("ana@correo.mx", "secreto"));
  act(() => ended());
  expect(result.current.user).toBeNull();
  expect(result.current.entered).toBe(false);
});
