import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import type { Song } from "./api/types";

export function renderApp(ui: ReactNode, route = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

export const song = (over: Partial<Song> = {}): Song => ({
  id: "s1",
  title: "Luz de carretera",
  artist_id: "a1",
  artist: "Marea Baja",
  album: "Noches",
  duration: 183,
  cover_url: null,
  source: "local",
  license: "CC BY",
  license_url: null,
  jamendo_url: null,
  genres: ["rock"],
  status: "published",
  available: true,
  ...over,
});

/**
 * Responde según la ruta, sin parámetros. La clave puede llevar método ("POST /api/x") cuando una ruta sirve para
 * varios. Una ruta sin respuesta falla la prueba de forma visible.
 */
export function routes(table: Record<string, unknown>) {
  return async (path: string, options?: { method?: string }) => {
    const bare = path.split("?")[0];
    const withMethod = `${options?.method ?? "GET"} ${bare}`;
    const key = withMethod in table ? withMethod : bare;
    if (key in table) {
      const value = table[key];
      if (value instanceof Error) throw value;
      return value;
    }
    throw new Error(`Ruta sin respuesta en la prueba: ${path}`);
  };
}
