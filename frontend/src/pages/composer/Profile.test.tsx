import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError, upload } from "../../api/client";
import { renderApp, routes } from "../../test-utils";
import { ComposerProfile } from "./Profile";

vi.mock("../../api/client", async (original) => ({
  ...(await original<typeof import("../../api/client")>()),
  api: vi.fn(),
  upload: vi.fn(),
}));

const artist = {
  id: "a1",
  name: "Marea",
  source: "local",
  bio: "Hola",
  photo_url: null,
  links: { web: "https://marea.example", otra: "https://otra.example" },
};

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(upload).mockReset();
  vi.mocked(api).mockImplementation(
    routes({ "/api/composer/profile": artist, "PUT /api/composer/profile": artist }) as typeof api,
  );
});

test("guarda los enlaces, sin los vacíos y sin perder los que no se ven", async () => {
  renderApp(<ComposerProfile />);
  const web = await screen.findByDisplayValue("https://marea.example");
  expect(web).toBe(screen.getByLabelText("Sitio web"));
  await userEvent.clear(web);
  await userEvent.type(screen.getByLabelText("Instagram"), "https://instagram.com/marea");
  await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
  await screen.findByText("Perfil guardado.");
  const call = vi.mocked(api).mock.calls.find(([, options]) => options?.method === "PUT")!;
  expect((call[1]?.json as { links: object }).links).toEqual({
    otra: "https://otra.example",
    instagram: "https://instagram.com/marea",
  });
});

test("sube la foto", async () => {
  vi.mocked(upload).mockResolvedValue({ ...artist, photo_url: "/media/foto.jpg" });
  renderApp(<ComposerProfile />);
  const file = new File(["x"], "foto.jpg", { type: "image/jpeg" });
  await userEvent.upload(await screen.findByLabelText("Foto"), file);
  expect(await screen.findByRole("status")).toHaveTextContent("Foto guardada.");
  const [path, form] = vi.mocked(upload).mock.calls[0];
  expect(path).toBe("/api/composer/profile/photo");
  expect((form as FormData).get("photo")).toBe(file);
});

test("una foto rechazada muestra el motivo", async () => {
  vi.mocked(upload).mockRejectedValue(new ApiError(422, "invalid_cover", "La imagen debe ser JPG o PNG"));
  renderApp(<ComposerProfile />);
  await userEvent.upload(await screen.findByLabelText("Foto"), new File(["x"], "foto.jpg", { type: "image/jpeg" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("La imagen debe ser JPG o PNG");
});
