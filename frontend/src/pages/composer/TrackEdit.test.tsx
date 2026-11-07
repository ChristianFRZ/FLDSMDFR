import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../../api/client";
import { renderApp, routes, song } from "../../test-utils";
import { TrackEdit } from "./TrackEdit";

vi.mock("../../api/client", async (original) => ({
  ...(await original<typeof import("../../api/client")>()),
  api: vi.fn(),
}));

const track = (over = {}) => ({
  ...song({ id: "t1", title: "Vieja", genres: ["rock"], license: "CC BY", status: "draft" }),
  album_id: null,
  publish_at: null,
  hidden_by_admin: false,
  hidden_reason: null,
  ...over,
});

function show(table: Record<string, unknown>) {
  vi.mocked(api).mockImplementation(routes({ "/api/composer/albums": [{ id: "al1", title: "Disco" }], ...table }) as typeof api);
  renderApp(
    <Routes>
      <Route path="/composer/tracks/:id" element={<TrackEdit />} />
      <Route path="/composer" element={<p>Tu música</p>} />
    </Routes>,
    "/composer/tracks/t1",
  );
}

beforeEach(() => {
  vi.mocked(api).mockReset();
});

test("muestra los datos de la pista y guarda los cambios", async () => {
  show({ "/api/composer/tracks": [track()], "PATCH /api/composer/tracks/t1": track() });
  const title = await screen.findByLabelText("Título");
  expect(title).toHaveValue("Vieja");
  expect(screen.getByLabelText("Género")).toHaveValue("rock");
  await userEvent.clear(title);
  await userEvent.type(title, "Nueva");
  await userEvent.selectOptions(screen.getByLabelText("Álbum o EP"), "al1");
  await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
  expect(await screen.findByText("Tu música")).toBeInTheDocument();
  const call = vi.mocked(api).mock.calls.find(([, options]) => options?.method === "PATCH")!;
  expect(call[1]?.json).toEqual({ title: "Nueva", genre: "rock", license: "CC BY", album_id: "al1" });
});

test("reprogramar manda la fecha nueva", async () => {
  const publish_at = "2030-01-02T03:04:00.000Z";
  show({ "/api/composer/tracks": [track({ status: "scheduled", publish_at })], "PATCH /api/composer/tracks/t1": track() });
  const date = await screen.findByLabelText("Fecha de publicación");
  await userEvent.clear(date);
  await userEvent.type(date, "2031-05-06T07:08");
  await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
  await screen.findByText("Tu música");
  const call = vi.mocked(api).mock.calls.find(([, options]) => options?.method === "PATCH")!;
  expect((call[1]?.json as { publish_at: string }).publish_at).toBe(new Date("2031-05-06T07:08").toISOString());
});

test("quitar la fecha devuelve la pista a borrador", async () => {
  const publish_at = "2030-01-02T03:04:00.000Z";
  show({ "/api/composer/tracks": [track({ status: "scheduled", publish_at })], "PATCH /api/composer/tracks/t1": track() });
  await userEvent.clear(await screen.findByLabelText("Fecha de publicación"));
  await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
  await screen.findByText("Tu música");
  const call = vi.mocked(api).mock.calls.find(([, options]) => options?.method === "PATCH")!;
  expect((call[1]?.json as { publish_at: null }).publish_at).toBeNull();
});

test("una pista publicada no ofrece fecha", async () => {
  show({ "/api/composer/tracks": [track({ status: "published" })] });
  await screen.findByLabelText("Título");
  expect(screen.queryByLabelText("Fecha de publicación")).not.toBeInTheDocument();
});

test("muestra el error del servidor", async () => {
  show({
    "/api/composer/tracks": [track()],
    "PATCH /api/composer/tracks/t1": new ApiError(422, "publish_at_past", "La fecha debe estar en el futuro"),
  });
  await screen.findByLabelText("Título");
  await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("La fecha debe estar en el futuro");
});

test("una pista que no es tuya no se puede editar", async () => {
  show({ "/api/composer/tracks": [] });
  expect(await screen.findByRole("alert")).toHaveTextContent("No encontramos esta pista");
});
