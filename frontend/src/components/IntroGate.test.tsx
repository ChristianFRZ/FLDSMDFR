import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { hasSession } from "../api/client";
import { IntroGate } from "./IntroGate";

vi.mock("../api/client", () => ({ hasSession: vi.fn(() => false) }));

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(hasSession).mockReturnValue(false);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const gate = () => (
  <IntroGate>
    <p>Hijos</p>
  </IntroGate>
);

test("muestra la apertura sin sesión", () => {
  render(gate());
  expect(screen.getByRole("status", { name: "Cargando MELOXO" })).toBeInTheDocument();
  expect(screen.getByText("Hijos")).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(1200));
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(screen.getByText("Hijos")).toBeInTheDocument();
});

test("no la muestra con sesión abierta", () => {
  vi.mocked(hasSession).mockReturnValue(true);
  render(gate());
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(screen.getByText("Hijos")).toBeInTheDocument();
});

test("se muestra de nuevo en cada carga de la página", () => {
  const first = render(gate());
  act(() => vi.advanceTimersByTime(1200));
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  first.unmount();
  render(gate());
  expect(screen.getByRole("status", { name: "Cargando MELOXO" })).toBeInTheDocument();
});

test("un clic la salta y los hijos siguen ahí", () => {
  render(gate());
  act(() => screen.getByRole("status").click());
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(screen.getByText("Hijos")).toBeInTheDocument();
});
