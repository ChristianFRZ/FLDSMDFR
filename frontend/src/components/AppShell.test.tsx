import { screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { useAuth } from "../auth/AuthContext";
import { renderApp } from "../test-utils";
import { AppShell } from "./AppShell";

vi.mock("../auth/AuthContext", () => ({ useAuth: vi.fn() }));

function asRole(role: string) {
  vi.mocked(useAuth).mockReturnValue({ user: { id: "u", display_name: "Ana", role } } as never);
  renderApp(<AppShell />);
}

test("menú de Oyente no muestra vistas de otros roles", () => {
  asRole("listener");
  expect(screen.getByRole("link", { name: "Estadísticas" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Tu música" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Administración" })).not.toBeInTheDocument();
});

test("menú de Compositor agrega su música", () => {
  asRole("composer");
  expect(screen.getByRole("link", { name: "Tu música" })).toHaveAttribute("href", "/composer");
  expect(screen.queryByRole("link", { name: "Administración" })).not.toBeInTheDocument();
});

test("menú de Administrador agrega el panel", () => {
  asRole("admin");
  expect(screen.getByRole("link", { name: "Administración" })).toHaveAttribute("href", "/admin");
});
