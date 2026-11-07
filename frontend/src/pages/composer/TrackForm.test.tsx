import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError, upload } from "../../api/client";
import { renderApp } from "../../test-utils";
import { TrackForm } from "./TrackForm";

vi.mock("../../api/client", async (original) => ({
  ...(await original<typeof import("../../api/client")>()),
  api: vi.fn(),
  upload: vi.fn(),
}));

const file = (name: string, type: string, bytes = 10) => new File([new Uint8Array(bytes)], name, { type });

async function fill(audio: File) {
  await userEvent.type(screen.getByLabelText("Título"), "Mi pista");
  await userEvent.type(screen.getByLabelText("Género"), "rock");
  await userEvent.type(screen.getByLabelText("Licencia"), "CC BY");
  await userEvent.upload(screen.getByLabelText("Archivo MP3"), audio);
}

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(api).mockResolvedValue([]);
  vi.mocked(upload).mockReset();
});

test("formulario valida tipo antes de subir", async () => {
  renderApp(<TrackForm />);
  // `accept` solo filtra el diálogo del sistema: arrastrar o forzar el archivo lo salta.
  const user = userEvent.setup({ applyAccept: false });
  await user.upload(screen.getByLabelText("Portada (opcional)"), file("x.gif", "image/gif"));
  expect(await screen.findByText("La portada debe ser JPG o PNG.")).toBeInTheDocument();
  expect(upload).not.toHaveBeenCalled();
});

test("formulario valida tamaño antes de subir", async () => {
  renderApp(<TrackForm />);
  const big = file("a.mp3", "audio/mpeg");
  Object.defineProperty(big, "size", { value: 16 * 1024 * 1024 });
  await fill(big);
  expect(screen.getByText("El MP3 supera 15 MB.")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Subir pista" }));
  expect(upload).not.toHaveBeenCalled();
});

test("muestra progreso de subida", async () => {
  let report: (fraction: number) => void = () => undefined;
  vi.mocked(upload).mockImplementation((_, __, onProgress) => {
    report = onProgress!;
    return new Promise(() => undefined);
  });
  renderApp(<TrackForm />);
  await fill(file("a.mp3", "audio/mpeg"));
  await userEvent.click(screen.getByRole("button", { name: "Subir pista" }));
  await waitFor(() => expect(upload).toHaveBeenCalled());
  act(() => report(0.42));
  expect(screen.getByRole("progressbar", { name: "Subiendo" })).toHaveAttribute("value", "0.42");
  expect(screen.getByText("42 %")).toBeInTheDocument();
});

test("error del servidor por archivo inválido se muestra en el campo", async () => {
  vi.mocked(upload).mockRejectedValue(new ApiError(422, "invalid_audio", "El archivo no es un MP3 válido"));
  renderApp(<TrackForm />);
  await fill(file("a.mp3", "audio/mpeg"));
  await userEvent.click(screen.getByRole("button", { name: "Subir pista" }));
  const message = await screen.findByText("El archivo no es un MP3 válido");
  expect(screen.getByLabelText("Archivo MP3")).toHaveAttribute("aria-describedby", message.id);
});
