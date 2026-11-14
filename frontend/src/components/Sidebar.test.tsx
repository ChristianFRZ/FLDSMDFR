import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { renderApp, routes } from "../test-utils";
import { resetLibraryPrefs } from "./libraryPrefs";
import { Sidebar } from "./Sidebar";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));

const tape = (id: string, title: string) => ({
  id,
  title,
  color: "pink",
  is_creator: true,
  member_count: 2,
  track_count: 3,
  max_tracks: 12,
});

beforeEach(() => {
  localStorage.clear();
  resetLibraryPrefs();
  vi.mocked(api).mockImplementation(
    routes({
      "/api/tapes": [tape("t1", "Zeta"), tape("t2", "Alfa"), tape("t3", "Mitad")],
      "/api/tapes/invites/pending": [{ invite_id: "i1", tape_id: "t9", title: "Invitada", color: "pink", inviter: "Ana", expires_at: null }],
      "/api/playlists": [
        { id: "p1", owner_id: "u1", name: "Viaje", is_public: false, created_at: "2026-01-01" },
        { id: "p2", owner_id: "u1", name: "Estudio", is_public: false, created_at: "2026-01-02" },
      ],
      "/api/follows": [
        { id: "a1", name: "Marea Baja", source: "local", bio: null, photo_url: null, links: null },
        { id: "a2", name: "Cobre", source: "local", bio: null, photo_url: null, links: null },
      ],
    }) as typeof api,
  );
});

const rowNames = () =>
  screen.getAllByRole("link").map((link) => link.textContent ?? "").filter((text) => !text.startsWith("Crear"));

test("los casetes salen en el orden que llega", async () => {
  renderApp(<Sidebar />);
  await screen.findByText("Zeta");
  expect(rowNames().slice(0, 3).map((name) => name.split(/\d/)[0])).toEqual(["Zeta", "Alfa", "Mitad"]);
});

test("fijar un casete lo sube al principio", async () => {
  renderApp(<Sidebar />);
  await screen.findByText("Mitad");
  const pin = screen.getByRole("button", { name: "Fijar Mitad" });
  expect(pin).toHaveAttribute("aria-pressed", "false");
  await userEvent.click(pin);
  expect(screen.getByRole("button", { name: "Fijar Mitad" })).toHaveAttribute("aria-pressed", "true");
  expect(rowNames()[0]).toMatch(/^Mitad/);
});

test("soltar un casete fijado lo devuelve a su sitio", async () => {
  renderApp(<Sidebar />);
  await screen.findByText("Mitad");
  await userEvent.click(screen.getByRole("button", { name: "Fijar Mitad" }));
  await userEvent.click(screen.getByRole("button", { name: "Fijar Mitad" }));
  expect(rowNames()[0]).toMatch(/^Zeta/);
});

test("ordenar por nombre", async () => {
  renderApp(<Sidebar />);
  await screen.findByText("Zeta");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Ordenar biblioteca" }), "name");
  expect(rowNames().slice(0, 3).map((name) => name.split(/\d/)[0])).toEqual(["Alfa", "Mitad", "Zeta"]);
});

test("por nombre, lo fijado sigue primero", async () => {
  renderApp(<Sidebar />);
  await screen.findByText("Zeta");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Ordenar biblioteca" }), "name");
  await userEvent.click(screen.getByRole("button", { name: "Fijar Zeta" }));
  expect(rowNames()[0]).toMatch(/^Zeta/);
});

test("las invitaciones pendientes no se fijan", async () => {
  renderApp(<Sidebar />);
  await screen.findByText("Invitada");
  expect(screen.queryByRole("button", { name: "Fijar Invitada" })).not.toBeInTheDocument();
});

test("las playlists también se fijan y se ordenan", async () => {
  renderApp(<Sidebar />);
  await userEvent.click(screen.getByRole("button", { name: "Playlists" }));
  await screen.findByText("Viaje");
  await userEvent.click(screen.getByRole("button", { name: "Fijar Estudio" }));
  const links = within(document.querySelector(".lib") as HTMLElement).getAllByRole("link");
  expect(links.map((link) => link.textContent)).toEqual(["Estudio", "Viaje"]);
});

test("los artistas también se fijan", async () => {
  renderApp(<Sidebar />);
  await userEvent.click(screen.getByRole("button", { name: "Artistas" }));
  await screen.findByText("Marea Baja");
  await userEvent.click(screen.getByRole("button", { name: "Fijar Cobre" }));
  const links = within(document.querySelector(".lib") as HTMLElement).getAllByRole("link");
  expect(links.map((link) => link.textContent)).toEqual(["Cobre", "Marea Baja"]);
});
