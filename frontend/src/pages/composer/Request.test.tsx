import { screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../../api/client";
import { renderApp } from "../../test-utils";
import { ComposerRequest } from "./Request";

vi.mock("../../api/client", async (original) => ({
  ...(await original<typeof import("../../api/client")>()),
  api: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(api).mockReset();
});

test("Oyente ve la solicitud", async () => {
  vi.mocked(api).mockResolvedValue([]);
  renderApp(<ComposerRequest />);
  expect(await screen.findByRole("button", { name: "Solicitar ser Compositor" })).toBeInTheDocument();
});

test("con pendiente no puede enviar otra", async () => {
  vi.mocked(api).mockResolvedValue([{ id: "r1", status: "pending", reason: null }]);
  renderApp(<ComposerRequest />);
  expect(await screen.findByText("Tu solicitud está en revisión.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Solicitar ser Compositor" })).not.toBeInTheDocument();
});

test("rechazada muestra el motivo y deja volver a pedir", async () => {
  vi.mocked(api).mockResolvedValue([{ id: "r1", status: "rejected", reason: "Falta material" }]);
  renderApp(<ComposerRequest />);
  expect(await screen.findByText(/Falta material/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Solicitar ser Compositor" })).toBeInTheDocument();
});
