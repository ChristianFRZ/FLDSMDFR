import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSyncExternalStore } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { renderApp, song } from "../test-utils";
import { PlayerBar } from "./PlayerBar";

const store = vi.hoisted(() => {
  const listeners = new Set<() => void>();
  let player: Record<string, unknown> = {};
  return {
    get: () => player,
    set: (next: Record<string, unknown>) => {
      player = { ...player, ...next };
      listeners.forEach((listener) => listener());
    },
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
});

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));
vi.mock("./PlayerProvider", () => ({
  usePlayer: () => useSyncExternalStore(store.subscribe, store.get),
}));

let fullscreen: Element | null = null;

beforeEach(() => {
  fullscreen = null;
  vi.mocked(api).mockResolvedValue([]);
  store.set({
    current: song(),
    queue: [song()],
    context: null,
    isPlaying: true,
    position: 0,
    duration: 183,
    volume: 1,
    shuffle: false,
    repeat: "off",
    notice: null,
  });
  Object.defineProperty(document, "fullscreenElement", { configurable: true, get: () => fullscreen });
  // Como en el navegador, el cambio y su evento llegan después de la llamada.
  Element.prototype.requestFullscreen = async function requestFullscreen(this: Element) {
    await Promise.resolve();
    fullscreen = this;
    document.dispatchEvent(new Event("fullscreenchange"));
  };
  document.exitFullscreen = async () => {
    await Promise.resolve();
    fullscreen = null;
    document.dispatchEvent(new Event("fullscreenchange"));
  };
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("la pantalla completa sigue abierta mientras avanza la canción", async () => {
  renderApp(<PlayerBar />);
  await userEvent.click(screen.getByRole("button", { name: "Pantalla completa" }));
  expect(screen.getByRole("dialog", { name: "Pantalla completa" })).toBeInTheDocument();

  await act(async () => {
    store.set({ position: 1 });
    await new Promise((resolve) => setTimeout(resolve));
  });

  expect(screen.getByRole("dialog", { name: "Pantalla completa" })).toBeInTheDocument();
  expect(document.fullscreenElement).not.toBeNull();
});

test("cada pista de la cola se puede quitar y mover", async () => {
  const removeFromQueue = vi.fn();
  const moveInQueue = vi.fn();
  store.set({
    queue: [song({ id: "s2", title: "Otra" }), song({ id: "s3", title: "Tercera" })],
    removeFromQueue,
    moveInQueue,
    jump: vi.fn(),
  });
  renderApp(<PlayerBar />);
  await userEvent.click(screen.getByRole("button", { name: "Cola" }));

  await userEvent.click(screen.getByRole("button", { name: "Quitar Tercera de la cola" }));
  expect(removeFromQueue).toHaveBeenCalledWith(1);

  await userEvent.click(screen.getByRole("button", { name: "Subir Tercera en la cola" }));
  expect(moveInQueue).toHaveBeenCalledWith(1, 0);

  await userEvent.click(screen.getByRole("button", { name: "Bajar Otra en la cola" }));
  expect(moveInQueue).toHaveBeenCalledWith(0, 1);
});

test("la primera de la cola no se puede subir ni la última bajar", async () => {
  store.set({
    queue: [song({ id: "s2", title: "Otra" }), song({ id: "s3", title: "Tercera" })],
    removeFromQueue: vi.fn(),
    moveInQueue: vi.fn(),
    jump: vi.fn(),
  });
  renderApp(<PlayerBar />);
  await userEvent.click(screen.getByRole("button", { name: "Cola" }));
  expect(screen.getByRole("button", { name: "Subir Otra en la cola" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Bajar Tercera en la cola" })).toBeDisabled();
});

test("el temporizador ofrece sus opciones", async () => {
  const setSleepTimer = vi.fn();
  store.set({ sleepTimer: null, setSleepTimer });
  renderApp(<PlayerBar />);
  await userEvent.click(screen.getByRole("button", { name: "Temporizador" }));

  await userEvent.click(screen.getByRole("button", { name: "15 minutos" }));
  expect(setSleepTimer).toHaveBeenLastCalledWith({ minutes: 15 });
  await userEvent.click(screen.getByRole("button", { name: "30 minutos" }));
  expect(setSleepTimer).toHaveBeenLastCalledWith({ minutes: 30 });
  await userEvent.click(screen.getByRole("button", { name: "1 hora" }));
  expect(setSleepTimer).toHaveBeenLastCalledWith({ minutes: 60 });
  await userEvent.click(screen.getByRole("button", { name: "Al terminar la pista" }));
  expect(setSleepTimer).toHaveBeenLastCalledWith("track");
  expect(screen.queryByRole("button", { name: "Desactivar temporizador" })).not.toBeInTheDocument();
});

test("con el temporizador activo dice cuándo se detiene y se puede desactivar", async () => {
  const setSleepTimer = vi.fn();
  store.set({ sleepTimer: { kind: "minutes", endsAt: new Date(2030, 0, 1, 22, 40).getTime() }, setSleepTimer });
  renderApp(<PlayerBar />);
  await userEvent.click(screen.getByRole("button", { name: "Temporizador" }));
  expect(screen.getByText(/Se detiene a las 22:40/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Desactivar temporizador" }));
  expect(setSleepTimer).toHaveBeenCalledWith(null);
});

test("con el temporizador de pista activo lo dice con palabras", async () => {
  store.set({ sleepTimer: { kind: "track" }, setSleepTimer: vi.fn() });
  renderApp(<PlayerBar />);
  await userEvent.click(screen.getByRole("button", { name: "Temporizador" }));
  expect(screen.getByText("Se detiene al terminar esta pista.")).toBeInTheDocument();
});

test("el botón de salir cierra la pantalla completa", async () => {
  renderApp(<PlayerBar />);
  await userEvent.click(screen.getByRole("button", { name: "Pantalla completa" }));

  await userEvent.click(screen.getByRole("button", { name: "Salir de pantalla completa" }));

  expect(screen.queryByRole("dialog", { name: "Pantalla completa" })).not.toBeInTheDocument();
  await vi.waitFor(() => expect(document.fullscreenElement).toBeNull());
});
