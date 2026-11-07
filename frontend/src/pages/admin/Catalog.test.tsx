import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../../api/client";
import { renderApp, routes, song } from "../../test-utils";
import { Catalog } from "./Catalog";

vi.mock("../../api/client", async (original) => ({
  ...(await original<typeof import("../../api/client")>()),
  api: vi.fn(),
}));

const job = { id: "j1", status: "running", params: {}, offset: 0, imported: 37, error: null, created_at: "2026-11-01T00:00:00Z" };

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(api).mockImplementation(
    routes({
      "GET /api/admin/songs": { items: [], total: 0, page: 1, size: 20 },
      "GET /api/admin/catalog/import": [],
      "POST /api/admin/catalog/import": { job_id: "j1" },
      "GET /api/admin/catalog/import/j1": job,
    }),
  );
});

test("importación muestra avance consultando job_id", async () => {
  renderApp(<Catalog />);
  await userEvent.type(screen.getByLabelText("Géneros"), "rock, jazz");
  await userEvent.click(screen.getByRole("button", { name: "Importar de Jamendo" }));
  expect(api).toHaveBeenCalledWith(
    "/api/admin/catalog/import",
    expect.objectContaining({ json: { genres: ["rock", "jazz"], limit_per_genre: 50 } }),
  );
  expect(await screen.findByText("En curso: 37 pistas importadas")).toBeInTheDocument();
  expect(api).toHaveBeenCalledWith("/api/admin/catalog/import/j1");
});

const listed = (over: object) => ({ items: [song({ status: "hidden", available: false, ...over })], total: 1, page: 1, size: 20 });

function withSongs(page: unknown) {
  vi.mocked(api).mockImplementation(
    routes({ "GET /api/admin/songs": page, "GET /api/admin/catalog/import": [] }),
  );
}

test("una pista que ocultó su Compositor no ofrece Restaurar", async () => {
  withSongs(listed({ hidden_by_admin: false }));
  renderApp(<Catalog />);
  expect(await screen.findByText("Oculta por su Compositor")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Restaurar" })).not.toBeInTheDocument();
});

test("una pista que ocultó un administrador se puede restaurar", async () => {
  withSongs(listed({ hidden_by_admin: true }));
  renderApp(<Catalog />);
  expect(await screen.findByRole("button", { name: "Restaurar" })).toBeInTheDocument();
});

test("los estados se leen en español", async () => {
  withSongs(listed({ status: "scheduled", hidden_by_admin: false }));
  renderApp(<Catalog />);
  expect(await screen.findByText("Programada")).toBeInTheDocument();
});
