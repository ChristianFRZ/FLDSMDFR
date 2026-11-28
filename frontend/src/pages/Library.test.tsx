import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { resetLibraryPrefs } from "../components/libraryPrefs";
import { renderApp, routes } from "../test-utils";
import { Library } from "./Library";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));

test("si no se puede entrar al casete, Biblioteca dice por qué", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      "/api/tapes": [],
      "/api/playlists": [],
      "/api/follows": [],
      "/api/tapes/invites/pending": [{ invite_id: "i1", inviter: "Ana", title: "Viaje" }],
      "POST /api/tapes/claims/i1/join": new ApiError(409, "tape_full_members", "El casete ya tiene todos sus miembros"),
    }) as typeof api,
  );
  renderApp(<Library />);
  await userEvent.click(await screen.findByRole("button", { name: "Unirme al casete" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("El casete ya tiene todos sus miembros");
});

const playlist = (id: string, name: string) => ({ id, owner_id: "u1", name, is_public: false, created_at: "2026-01-01" });
const artist = (id: string, name: string) => ({ id, name, source: "local", bio: null, photo_url: null, links: null });

const listNames = (heading: string) => {
  const list = screen.getByRole("heading", { name: heading }).nextElementSibling?.matches("ul.link-list")
    ? screen.getByRole("heading", { name: heading }).nextElementSibling!
    : screen.getByRole("heading", { name: heading }).nextElementSibling!.nextElementSibling!;
  return [...list.querySelectorAll("a")].map((link) => link.textContent);
};

beforeEach(() => {
  localStorage.clear();
  resetLibraryPrefs();
  vi.mocked(api).mockImplementation(
    routes({
      "/api/tapes": [],
      "/api/tapes/invites/pending": [],
      "/api/playlists": [playlist("p1", "Viaje"), playlist("p2", "Estudio")],
      "/api/follows": [artist("a1", "Marea Baja"), artist("a2", "Cobre")],
    }) as typeof api,
  );
});

test("las playlists y los artistas se fijan desde Biblioteca", async () => {
  renderApp(<Library />);
  await screen.findByText("Viaje");
  await userEvent.click(screen.getByRole("button", { name: "Fijar Estudio" }));
  await userEvent.click(screen.getByRole("button", { name: "Fijar Cobre" }));
  expect(listNames("Playlists")).toEqual(["Estudio", "Viaje"]);
  expect(listNames("Artistas que sigues")).toEqual(["Cobre", "Marea Baja"]);
});

test("Biblioteca ordena por nombre", async () => {
  renderApp(<Library />);
  await screen.findByText("Viaje");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Ordenar biblioteca" }), "name");
  expect(listNames("Playlists")).toEqual(["Estudio", "Viaje"]);
  expect(listNames("Artistas que sigues")).toEqual(["Cobre", "Marea Baja"]);
});
