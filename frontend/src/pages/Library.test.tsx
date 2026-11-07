import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { renderApp, routes } from "../test-utils";
import { Library } from "./Library";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));

test("si no se puede entrar al casete, Biblioteca dice por qué", async () => {
  vi.mocked(api).mockImplementation(
    routes({
      "/api/tapes": [],
      "/api/playlists": [],
      "/api/follows": [],
      "/api/tapes/invites/pending": [{ invite_id: "i1", inviter: "Ana", title: "Viaje" }],
      "POST /api/tapes/claims/i1/join": new ApiError(409, "tape_full_members", "El casete ya tiene todos sus miembros"),
    }) as typeof api,
  );
  renderApp(<Library />);
  await userEvent.click(await screen.findByRole("button", { name: "Unirme al casete" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("El casete ya tiene todos sus miembros");
});
