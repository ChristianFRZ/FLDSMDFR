import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { renderApp } from "../test-utils";
import { resetTheme } from "../theme";
import { Profile } from "./Profile";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: { email: "ana@correo.mx", display_name: "Ana", role: "composer" }, logout: vi.fn() }),
}));

beforeEach(() => {
  localStorage.clear();
  document.head.innerHTML = '<meta name="theme-color" content="#141317"><meta name="color-scheme" content="dark">';
  act(() => resetTheme());
});

test("la apariencia ofrece sistema, oscuro y claro, y empieza en oscuro", () => {
  renderApp(<Profile />);
  const group = screen.getByRole("radiogroup", { name: "Apariencia" });
  expect(group).toBeInTheDocument();
  expect(screen.getByRole("radio", { name: "Sistema" })).not.toBeChecked();
  expect(screen.getByRole("radio", { name: "Oscuro" })).toBeChecked();
  expect(screen.getByRole("radio", { name: "Claro" })).not.toBeChecked();
});

test("elegir claro cambia la página y se recuerda", async () => {
  renderApp(<Profile />);
  await userEvent.click(screen.getByRole("radio", { name: "Claro" }));
  expect(screen.getByRole("radio", { name: "Claro" })).toBeChecked();
  expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  expect(localStorage.getItem("meloxo.theme")).toBe("light");
});

test("se puede volver a oscuro", async () => {
  renderApp(<Profile />);
  await userEvent.click(screen.getByRole("radio", { name: "Claro" }));
  await userEvent.click(screen.getByRole("radio", { name: "Oscuro" }));
  expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
});
