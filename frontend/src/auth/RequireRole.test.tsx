import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { expect, test, vi } from "vitest";
import { renderApp } from "../test-utils";
import { useAuth } from "./AuthContext";
import { RequireRole } from "./RequireRole";

vi.mock("./AuthContext", () => ({ useAuth: vi.fn() }));

const app = (
  <Routes>
    <Route index element={<p>Inicio</p>} />
    <Route element={<RequireRole roles={["admin"]} />}>
      <Route path="admin" element={<p>Panel</p>} />
    </Route>
  </Routes>
);

test("rutas de admin redirigen a Inicio a otros roles", () => {
  vi.mocked(useAuth).mockReturnValue({ user: { role: "listener" } } as never);
  renderApp(app, "/admin");
  expect(screen.getByText("Inicio")).toBeInTheDocument();
  expect(screen.queryByText("Panel")).not.toBeInTheDocument();
});

test("el rol correcto entra", () => {
  vi.mocked(useAuth).mockReturnValue({ user: { role: "admin" } } as never);
  renderApp(app, "/admin");
  expect(screen.getByText("Panel")).toBeInTheDocument();
});
