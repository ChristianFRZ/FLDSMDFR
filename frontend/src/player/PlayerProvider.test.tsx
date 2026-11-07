import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { song } from "../test-utils";
import { PlayerProvider, usePlayer } from "./PlayerProvider";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));

const broken = song({ id: "rota", title: "Rota" });
const second = song({ id: "segunda", title: "Segunda" });
const third = song({ id: "tercera", title: "Tercera" });

function Probe({ songs }: { songs: ReturnType<typeof song>[] }) {
  const { play, current, isPlaying } = usePlayer();
  return (
    <>
      <button type="button" onClick={() => play(songs)}>Empezar</button>
      <p data-testid="current">{current?.title}</p>
      <p data-testid="playing">{String(isPlaying)}</p>
    </>
  );
}

beforeEach(() => {
  vi.mocked(api).mockImplementation((async (path: string) =>
    path.includes("stream-ticket") ? { ticket: "t" } : {}) as typeof api);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
  vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(function play(this: HTMLMediaElement) {
    if (!this.src.includes("/rota/")) {
      Object.defineProperty(this, "error", { value: null, configurable: true });
      return Promise.resolve();
    }
    // Como el navegador: el elemento queda con error, lanza su evento y además rechaza play().
    Object.defineProperty(this, "error", { value: { code: 4 }, configurable: true });
    setTimeout(() => this.dispatchEvent(new Event("error")), 0);
    return Promise.reject(new DOMException("sin fuente", "NotSupportedError"));
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function start(songs: ReturnType<typeof song>[]) {
  render(<PlayerProvider><Probe songs={songs} /></PlayerProvider>);
  await act(async () => screen.getByRole("button", { name: "Empezar" }).click());
  await act(async () => new Promise((resolve) => setTimeout(resolve, 50)));
}

test("una pista rota salta solo a la siguiente", async () => {
  await start([broken, second, third]);
  await waitFor(() => expect(screen.getByTestId("current")).toHaveTextContent("Segunda"));
  await act(async () => new Promise((resolve) => setTimeout(resolve, 50)));
  expect(screen.getByTestId("current")).toHaveTextContent("Segunda");
});

test("si la penúltima está rota, la última sigue sonando", async () => {
  await start([broken, third]);
  await waitFor(() => expect(screen.getByTestId("current")).toHaveTextContent("Tercera"));
  await act(async () => new Promise((resolve) => setTimeout(resolve, 50)));
  expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled();
});
