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

test("el botón de salir cierra la pantalla completa", async () => {
  renderApp(<PlayerBar />);
  await userEvent.click(screen.getByRole("button", { name: "Pantalla completa" }));

  await userEvent.click(screen.getByRole("button", { name: "Salir de pantalla completa" }));

  expect(screen.queryByRole("dialog", { name: "Pantalla completa" })).not.toBeInTheDocument();
  await vi.waitFor(() => expect(document.fullscreenElement).toBeNull());
});
