import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { renderApp, song } from "../test-utils";
import { TapeDetail } from "./TapeDetail";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));
vi.mock("../player/PlayerProvider", () => ({ usePlayer: () => ({ play: vi.fn() }) }));
vi.mock("../components/AddSong", () => ({ useAddSong: () => vi.fn() }));

const track = (n: number, over = {}) => ({
  id: `k${n}`,
  position: n,
  side: n <= 6 ? "A" : "B",
  song: song({ id: `s${n}`, title: `Pista ${n}` }),
  added_by: "u1",
  added_by_name: "Ana",
  dedication: null,
  can_remove: true,
  ...over,
});

const tape = (tracks: unknown[], over = {}) => ({
  id: "t1",
  title: "Viaje",
  color: "teal",
  creator_id: "u1",
  is_creator: true,
  version: 4,
  created_at: "2026-11-01T00:00:00Z",
  max_tracks: 12,
  max_members: 8,
  degraded: false,
  members: [{ user_id: "u1", name: "Ana", joined_at: "2026-11-01T00:00:00Z" }],
  tracks,
  invites: [],
  ...over,
});

function serve(body: unknown, overrides: Record<string, unknown> = {}) {
  vi.mocked(api).mockImplementation((async (path: string, options?: { method?: string }) => {
    const key = `${options?.method ?? "GET"} ${path.split("?")[0]}`;
    if (key in overrides) {
      const value = overrides[key];
      if (value instanceof Error) throw value;
      return value;
    }
    if (key === "GET /api/tapes/t1") return body;
    if (key === "GET /api/songs") return { items: [song({ id: "nueva", title: "Nueva" })], total: 1, page: 1, size: 8 };
    throw new Error(`Ruta sin respuesta: ${key}`);
  }) as typeof api);
}

const show = () =>
  renderApp(<Routes><Route path="/tapes/:id" element={<TapeDetail />} /></Routes>, "/tapes/t1");

const refetches = () => vi.mocked(api).mock.calls.filter((c) => c[0] === "/api/tapes/t1").length;

beforeEach(() => {
  vi.mocked(api).mockReset();
});

test("separa Lado A y Lado B por posición", async () => {
  serve(tape([1, 2, 7].map((n) => track(n))));
  show();
  const a = await screen.findByRole("region", { name: "Lado A" });
  const b = screen.getByRole("region", { name: "Lado B" });
  expect(within(a).getByText("Pista 1")).toBeInTheDocument();
  expect(within(a).getByText("Pista 2")).toBeInTheDocument();
  expect(within(b).getByText("Pista 7")).toBeInTheDocument();
});

test("muestra lugares libres", async () => {
  serve(tape([track(1)]));
  show();
  expect(await screen.findByText("Quedan 11 lugares")).toBeInTheDocument();
});

test("lleno, desactiva agregar", async () => {
  serve(tape(Array.from({ length: 12 }, (_, i) => track(i + 1))));
  show();
  expect(await screen.findByText("Casete lleno")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Agregar pista" })).toBeDisabled();
});

test("409 al agregar explica que el casete se llenó y recarga", async () => {
  serve(tape([track(1)]), { "POST /api/tapes/t1/tracks": new ApiError(409, "tape_full", "El casete ya está lleno") });
  show();
  await userEvent.click(await screen.findByRole("button", { name: "Agregar pista" }));
  await userEvent.type(screen.getByRole("searchbox", { name: "Buscar pista para el casete" }), "nu");
  await userEvent.click(await screen.findByRole("button", { name: "Elegir Nueva" }));
  const before = refetches();
  await userEvent.click(screen.getByRole("button", { name: "Agregar al casete" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Alguien ocupó el último lugar");
  await waitFor(() => expect(refetches()).toBeGreaterThan(before));
});

test("409 al reordenar avisa y recarga el orden", async () => {
  serve(tape([track(1), track(2)]), {
    "PUT /api/tapes/t1/order": new ApiError(409, "tape_version_conflict", "Alguien cambió el casete."),
  });
  show();
  await userEvent.click(await screen.findByRole("button", { name: "Bajar Pista 1" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Alguien cambió el casete");
  await waitFor(() => expect(refetches()).toBeGreaterThan(1));
});

test("reordenar funciona con teclado", async () => {
  serve(tape([track(1), track(2)]), { "PUT /api/tapes/t1/order": { version: 5 } });
  show();
  const down = await screen.findByRole("button", { name: "Bajar Pista 1" });
  down.focus();
  await userEvent.keyboard("{Enter}");
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith("/api/tapes/t1/order", {
      method: "PUT",
      json: { version: 4, track_ids: ["k2", "k1"] },
    }),
  );
});

test("la primera pista no sube y la última no baja", async () => {
  serve(tape([track(1), track(2)]));
  show();
  expect(await screen.findByRole("button", { name: "Subir Pista 1" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Bajar Pista 2" })).toBeDisabled();
});

test("quitar solo aparece para quien agregó o el creador", async () => {
  serve(tape([track(1), track(2, { can_remove: false })], { is_creator: false }));
  show();
  expect(await screen.findByRole("button", { name: "Quitar Pista 1" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Quitar Pista 2" })).not.toBeInTheDocument();
});

test("pista no disponible conserva su lugar y dedicatoria", async () => {
  serve(
    tape([
      track(1, { song: song({ id: "s1", title: "Oculta", available: false }), dedication: "Te la dejo" }),
      track(2),
    ]),
  );
  show();
  expect(await screen.findByText("Oculta")).toBeInTheDocument();
  expect(screen.getByText("No disponible")).toBeInTheDocument();
  expect(screen.getByText("Te la dejo")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Reproducir Oculta" })).toBeDisabled();
});

test("solo el creador ve eliminar casete", async () => {
  serve(tape([], { is_creator: false }));
  show();
  await screen.findByRole("heading", { name: "Viaje" });
  expect(screen.queryByRole("button", { name: "Eliminar casete" })).not.toBeInTheDocument();
});

test("sin ser miembro explica que necesita invitación", async () => {
  serve(null, { "GET /api/tapes/t1": new ApiError(403, "not_a_member", "No eres miembro de este casete") });
  show();
  expect(await screen.findByRole("alert")).toHaveTextContent("necesitas una invitación");
});

test("con catálogo caído avisa y conserva la lista", async () => {
  serve(tape([track(1)], { degraded: true }));
  show();
  expect(await screen.findByText(/datos guardados/)).toBeInTheDocument();
  expect(screen.getByText("Pista 1")).toBeInTheDocument();
});
