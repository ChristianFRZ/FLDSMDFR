import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { TAPE_COLORS } from "../components/tapeColors";
import { renderApp } from "../test-utils";
import { TapeCreate } from "./TapeCreate";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(api).mockResolvedValue({ id: "t1", title: "Para el viaje", color: "#ff3d8b" });
});

const originalMatchMedia = window.matchMedia;

afterEach(() => {
  vi.useRealTimers();
  window.matchMedia = originalMatchMedia;
});

async function create() {
  await userEvent.type(screen.getByLabelText("Nombre"), "Para el viaje");
  await userEvent.click(screen.getByRole("button", { name: "Crear casete" }));
  await waitFor(() => expect(api).toHaveBeenCalled());
  return vi.mocked(api).mock.calls[0][1]?.json;
}

test("ofrece los doce colores del estante", () => {
  renderApp(<TapeCreate />);
  expect(TAPE_COLORS).toHaveLength(12);
  expect(screen.getAllByRole("radio")).toHaveLength(12);
  expect(screen.getByRole("radio", { name: "Rosa" })).toBeChecked();
});

test("crea el casete con el color elegido del estante", async () => {
  renderApp(<TapeCreate />);
  await userEvent.click(screen.getByRole("radio", { name: "Lima" }));
  expect(await create()).toEqual({ title: "Para el viaje", color: "#b6e03c" });
});

test("el color libre reemplaza la elección del estante", async () => {
  renderApp(<TapeCreate />);
  fireEvent.input(screen.getByLabelText("Color libre"), { target: { value: "#123456" } });
  expect(screen.getByRole("radio", { name: "Rosa" })).not.toBeChecked();
  expect(await create()).toEqual({ title: "Para el viaje", color: "#123456" });
});

/** Monta la página con una ruta destino para ver adónde navega al crear. */
function renderWithDestination() {
  renderApp(
    <Routes>
      <Route path="/" element={<TapeCreate />} />
      <Route path="/tapes/:id" element={<p>Página del casete</p>} />
    </Routes>,
  );
}

/** Envía el formulario con relojes falsos y deja que la mutación termine. */
async function submitWithFakeTimers() {
  fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Para el viaje" } });
  fireEvent.click(screen.getByRole("button", { name: "Crear casete" }));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

test("tras crear muestra \"Casete creado\" y navega a /tapes/t1 a los 900 ms", async () => {
  vi.useFakeTimers();
  renderWithDestination();
  await submitWithFakeTimers();
  expect(screen.getByRole("status", { name: "Casete creado" })).toBeInTheDocument();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(900);
  });
  expect(screen.getByText("Página del casete")).toBeInTheDocument();
  expect(screen.queryByRole("status", { name: "Casete creado" })).not.toBeInTheDocument();
});

test("no navega antes de tiempo", async () => {
  vi.useFakeTimers();
  renderWithDestination();
  await submitWithFakeTimers();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(899);
  });
  expect(screen.queryByText("Página del casete")).not.toBeInTheDocument();
  expect(screen.getByRole("status", { name: "Casete creado" })).toBeInTheDocument();
});

test("un clic salta la animación y navega", async () => {
  vi.useFakeTimers();
  renderWithDestination();
  await submitWithFakeTimers();
  fireEvent.click(screen.getByRole("status", { name: "Casete creado" }));
  expect(screen.getByText("Página del casete")).toBeInTheDocument();
});

test("con reduced-motion navega sin esperar", async () => {
  window.matchMedia = vi.fn((query: string) => ({
    matches: query === "(prefers-reduced-motion: reduce)",
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
  renderWithDestination();
  await create();
  expect(await screen.findByText("Página del casete", {}, { timeout: 200 })).toBeInTheDocument();
});

test("con error de API no muestra la animación y el botón sigue activo", async () => {
  vi.mocked(api).mockRejectedValue(new ApiError(400, "invalid", "Nombre no válido"));
  renderWithDestination();
  await create();
  expect(await screen.findByRole("alert")).toHaveTextContent("Nombre no válido");
  expect(screen.queryByRole("status", { name: "Casete creado" })).not.toBeInTheDocument();
  expect(screen.queryByText("Página del casete")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Crear casete" })).toBeEnabled();
});

test("Enter en el nombre con la animación en pantalla no crea otro casete", async () => {
  renderWithDestination();
  await create();
  expect(await screen.findByRole("status", { name: "Casete creado" })).toBeInTheDocument();
  const input = screen.getByLabelText("Nombre");
  // Como en el navegador: el keydown llega a la ventana (salta la animación) y su acción por defecto envía el
  // formulario antes de que React vuelva a pintar.
  act(() => {
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    input.closest("form")!.requestSubmit();
  });
  await new Promise((resolve) => setTimeout(resolve, 50));
  expect(api).toHaveBeenCalledTimes(1);
});

test("cualquier tecla salta la animación y navega", async () => {
  vi.useFakeTimers();
  renderWithDestination();
  await submitWithFakeTimers();
  fireEvent.keyDown(window, { key: "Escape" });
  expect(screen.getByText("Página del casete")).toBeInTheDocument();
});

test("con la animación en pantalla el formulario queda inerte", async () => {
  vi.useFakeTimers();
  renderWithDestination();
  await submitWithFakeTimers();
  expect(screen.getByLabelText("Nombre").closest(".tape-create")).toHaveAttribute("inert");
});
