import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { expect, test, vi } from "vitest";
import { api } from "../api/client";
import { renderApp, routes } from "../test-utils";
import { Artist } from "./Artist";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));
vi.mock("../player/PlayerProvider", () => ({ usePlayer: () => ({ play: vi.fn() }) }));

test("muestra la foto y solo los enlaces web", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      "/api/artists/a1": {
        id: "a1",
        name: "Marea",
        source: "local",
        bio: "",
        photo_url: "/media/foto.jpg",
        links: { web: "https://marea.example", malo: "javascript:alert(1)" },
        songs: [],
      },
      "/api/follows/ids": [],
    }) as typeof api,
  );
  renderApp(
    <Routes><Route path="/artists/:id" element={<Artist />} /></Routes>,
    "/artists/a1",
  );
  expect(await screen.findByRole("link", { name: "Sitio web" })).toHaveAttribute("href", "https://marea.example");
  expect(screen.getAllByRole("link")).toHaveLength(1);
  expect(screen.getByRole("img", { name: "Foto de Marea" })).toHaveAttribute("src", "/media/foto.jpg");
});
