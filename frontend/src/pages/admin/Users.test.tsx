import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../../api/client";
import { renderApp, routes } from "../../test-utils";
import { Users } from "./Users";

vi.mock("../../api/client", async (original) => ({
  ...(await original<typeof import("../../api/client")>()),
  api: vi.fn(),
}));

const ana = { id: "u1", email: "ana@meloxo.dev", display_name: "Ana", role: "admin", status: "active", created_at: "2026-11-01T00:00:00Z" };

beforeEach(() => {
  vi.mocked(api).mockReset();
});

test("409 de último administrador explica por qué y no cambia la fila", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      "GET /api/admin/users": { items: [ana], total: 1, page: 1, size: 20 },
      "POST /api/admin/users/u1/role": new ApiError(409, "last_admin", "Debe quedar al menos un administrador activo"),
    }),
  );
  renderApp(<Users />);
  const row = (await screen.findByText("ana@meloxo.dev")).closest("tr")!;
  const role = within(row).getByLabelText("Rol de Ana");
  await userEvent.selectOptions(role, "listener");
  expect(await screen.findByRole("alert")).toHaveTextContent("Debe quedar al menos un administrador activo");
  expect(role).toHaveValue("admin");
});

test("suspender pide confirmación antes de llamar al backend", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      "GET /api/admin/users": { items: [{ ...ana, role: "listener" }], total: 1, page: 1, size: 20 },
      "POST /api/admin/users/u1/suspend": { ...ana, status: "suspended" },
    }),
  );
  renderApp(<Users />);
  await userEvent.click(await screen.findByRole("button", { name: "Suspender a Ana" }));
  expect(api).not.toHaveBeenCalledWith("/api/admin/users/u1/suspend", expect.anything());
  await userEvent.click(screen.getByRole("button", { name: "Confirmar suspensión" }));
  expect(api).toHaveBeenCalledWith("/api/admin/users/u1/suspend", expect.objectContaining({ method: "POST" }));
});
