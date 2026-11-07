import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../../api/client";
import { renderApp, routes } from "../../test-utils";
import { Requests } from "./Requests";

vi.mock("../../api/client", async (original) => ({
  ...(await original<typeof import("../../api/client")>()),
  api: vi.fn(),
}));

const request = { id: "r1", user_id: "u1", message: "Toco jazz", status: "pending", reason: null, created_at: "2026-11-01T00:00:00Z" };

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(api).mockImplementation(
    routes({
      "GET /api/admin/composer-requests": { items: [request], total: 1, page: 1, size: 20 },
      "POST /api/admin/composer-requests/r1/reject": { ...request, status: "rejected" },
    }),
  );
});

test("rechazar solicitud pide motivo", async () => {
  renderApp(<Requests />);
  await userEvent.click(await screen.findByRole("button", { name: "Rechazar" }));
  const send = screen.getByRole("button", { name: "Confirmar rechazo" });
  expect(send).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Motivo del rechazo"), "Falta material");
  await userEvent.click(send);
  expect(api).toHaveBeenCalledWith(
    "/api/admin/composer-requests/r1/reject",
    expect.objectContaining({ json: { reason: "Falta material" } }),
  );
});
