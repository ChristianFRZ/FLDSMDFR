import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { renderApp, routes, song } from "../test-utils";
import { Home } from "./Home";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));
vi.mock("../player/PlayerProvider", () => ({ usePlayer: () => ({ play: vi.fn() }) }));

const empty = {
  "/api/tapes": [],
  "/api/tapes/invites/pending": [],
  "/api/playbacks/history": { items: [], total: 0, page: 1, size: 12 },
  "/api/releases": { scheduled: [], published: [], degraded: false },
};

beforeEach(() => {
  vi.mocked(api).mockReset();
});

test("Inicio con todo vacío invita a crear un casete", async () => {
  vi.mocked(api).mockImplementation(routes(empty) as typeof api);
  renderApp(<Home />);
  expect(await screen.findByRole("link", { name: "Crear tu primer casete" })).toHaveAttribute("href", "/tapes/new");
});

test("Inicio no tiene secciones de recomendación", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      ...empty,
      "/api/tapes": [{ id: "t1", title: "Viaje", color: "teal", is_creator: true, member_count: 2, track_count: 3 }],
      "/api/playbacks/history": {
        items: [{ playback_id: "p1", listened_seconds: 20, started_at: "2026-11-01T00:00:00Z", song: song() }],
        total: 1,
        page: 1,
        size: 12,
      },
    }) as typeof api,
  );
  renderApp(<Home />);
  await screen.findByText("Viaje");
  const headings = screen.getAllByRole("heading").map((h) => h.textContent);
  expect(headings).toEqual(["Tus casetes", "Seguir escuchando", "Lanzamientos de artistas que sigues"]);
  expect(document.body.textContent).not.toMatch(/recomend|para ti|descubr/i);
});

test("muestra invitaciones pendientes como nota", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      ...empty,
      "/api/tapes/invites/pending": [
        { invite_id: "i1", tape_id: "t9", title: "Noches de patio", color: "pink", inviter: "Leo", expires_at: null },
      ],
    }) as typeof api,
  );
  renderApp(<Home />);
  const note = (await screen.findByText(/Leo te invitó/)).closest(".note") as HTMLElement;
  expect(within(note).getByText(/Noches de patio/)).toBeInTheDocument();
  expect(within(note).getByRole("button", { name: "Unirme al casete" })).toBeInTheDocument();
});

test("lanzamientos programados muestran su fecha y no se reproducen", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      ...empty,
      "/api/releases": {
        scheduled: [{ song_id: "s9", title: "Pronto", artist_id: "a1", artist: "Marea Baja", publish_at: "2026-12-24T15:00:00Z" }],
        published: [],
        degraded: false,
      },
    }) as typeof api,
  );
  renderApp(<Home />);
  expect(await screen.findByText("Pronto")).toBeInTheDocument();
  expect(screen.getByText(/Sale el/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Reproducir Pronto/ })).not.toBeInTheDocument();
});

test("si catálogo falla, Inicio avisa y sigue en pie", async () => {
  vi.mocked(api).mockImplementation(
    routes({ ...empty, "/api/releases": { scheduled: [], published: [], degraded: true } }) as typeof api,
  );
  renderApp(<Home />);
  expect(await screen.findByText(/no están disponibles por ahora/)).toBeInTheDocument();
});

test("si no se puede entrar al casete, Inicio dice por qué", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      ...empty,
      "/api/tapes/invites/pending": [{ invite_id: "i1", inviter: "Ana", title: "Viaje" }],
      "POST /api/tapes/claims/i1/join": new ApiError(409, "tape_full_members", "El casete ya tiene todos sus miembros"),
    }) as typeof api,
  );
  renderApp(<Home />);
  await userEvent.click(await screen.findByRole("button", { name: "Unirme al casete" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("El casete ya tiene todos sus miembros");
});
