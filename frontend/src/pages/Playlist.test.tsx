import { screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { api } from "../api/client";
import { renderApp, routes, song } from "../test-utils";
import { Playlist } from "./Playlist";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));
vi.mock("../player/PlayerProvider", () => ({ usePlayer: () => ({ play: vi.fn() }) }));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("../components/AddSong", () => ({ useAddSong: () => vi.fn() }));

beforeEach(() => {
  vi.mocked(api).mockReset();
});

const body = {
  id: "p1",
  owner_id: "u1",
  name: "Viaje",
  is_public: false,
  created_at: "2026-11-01T00:00:00Z",
  degraded: true,
  songs: [song()],
};

test("playlist con degraded muestra aviso y conserva la lista", async () => {
  vi.mocked(api).mockImplementation(routes({ "/api/playlists/p1": body }) as typeof api);
  renderApp(
    <Routes><Route path="/playlists/:id" element={<Playlist />} /></Routes>,
    "/playlists/p1",
  );
  expect(await screen.findByText(/datos guardados/)).toBeInTheDocument();
  expect(screen.getByText("Luz de carretera")).toBeInTheDocument();
});
