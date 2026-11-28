import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

const extra = song({ id: "extra", title: "Extra" });

function QueueProbe() {
  const { play, playNext, addToQueue, removeFromQueue, moveInQueue, current, queue, notice } = usePlayer();
  return (
    <>
      <button type="button" onClick={() => play([second, third])}>Empezar</button>
      <button type="button" onClick={() => playNext(extra)}>Siguiente</button>
      <button type="button" onClick={() => addToQueue(extra)}>Al final</button>
      <button type="button" onClick={() => removeFromQueue(0)}>Quitar primera</button>
      <button type="button" onClick={() => moveInQueue(0, 1)}>Bajar primera</button>
      <p data-testid="current">{current?.title}</p>
      <p data-testid="queue">{queue.map((item) => item.title).join(",")}</p>
      <p data-testid="notice">{notice}</p>
    </>
  );
}

async function press(name: string) {
  await act(async () => screen.getByRole("button", { name }).click());
}

test("reproducir siguiente pone la pista primero en lo que sigue", async () => {
  render(<PlayerProvider><QueueProbe /></PlayerProvider>);
  await press("Empezar");
  await press("Siguiente");
  expect(screen.getByTestId("current")).toHaveTextContent("Segunda");
  expect(screen.getByTestId("queue")).toHaveTextContent("Extra,Tercera");
  expect(screen.getByTestId("notice")).toHaveTextContent("«Extra» sonará a continuación");
});

test("agregar a la cola pone la pista al final", async () => {
  render(<PlayerProvider><QueueProbe /></PlayerProvider>);
  await press("Empezar");
  await press("Al final");
  expect(screen.getByTestId("queue")).toHaveTextContent("Tercera,Extra");
  expect(screen.getByTestId("notice")).toHaveTextContent("«Extra» se agregó a la cola");
});

test("con la cola vacía, agregar una pista la reproduce", async () => {
  render(<PlayerProvider><QueueProbe /></PlayerProvider>);
  await press("Al final");
  await waitFor(() => expect(screen.getByTestId("current")).toHaveTextContent("Extra"));
  expect(screen.getByTestId("queue")).toBeEmptyDOMElement();
});

test("quitar y reordenar lo que sigue", async () => {
  render(<PlayerProvider><QueueProbe /></PlayerProvider>);
  await press("Empezar");
  await press("Al final");
  await press("Bajar primera");
  expect(screen.getByTestId("queue")).toHaveTextContent("Extra,Tercera");
  await press("Quitar primera");
  expect(screen.getByTestId("queue")).toHaveTextContent("Tercera");
});

function ShortcutProbe() {
  const { play, position, volume } = usePlayer();
  return (
    <>
      <button type="button" onClick={() => play([second, third])}>Empezar</button>
      <input aria-label="Escribir" />
      <p data-testid="position">{position}</p>
      <p data-testid="volume">{volume}</p>
    </>
  );
}

async function key(code: string, init: KeyboardEventInit = {}, target: Element | Window = window) {
  await act(async () => {
    fireEvent.keyDown(target, { code, key: code, ...init });
  });
}

async function startShortcuts() {
  render(<PlayerProvider><ShortcutProbe /></PlayerProvider>);
  await press("Empezar");
}

test("la flecha derecha adelanta 5 segundos y la izquierda retrocede", async () => {
  await startShortcuts();
  await key("ArrowRight");
  expect(screen.getByTestId("position")).toHaveTextContent(/^5$/);
  await key("ArrowRight");
  await key("ArrowLeft");
  expect(screen.getByTestId("position")).toHaveTextContent(/^5$/);
});

test("la flecha izquierda no baja de cero", async () => {
  await startShortcuts();
  await key("ArrowLeft");
  expect(screen.getByTestId("position")).toHaveTextContent(/^0$/);
});

test("las flechas con Alt, Ctrl o Cmd se dejan al navegador", async () => {
  await startShortcuts();
  await key("ArrowRight", { altKey: true });
  await key("ArrowRight", { ctrlKey: true });
  await key("ArrowRight", { metaKey: true });
  expect(screen.getByTestId("position")).toHaveTextContent(/^0$/);
});

test("las flechas no buscan mientras se escribe en un campo", async () => {
  await startShortcuts();
  await key("ArrowRight", {}, screen.getByLabelText("Escribir"));
  expect(screen.getByTestId("position")).toHaveTextContent(/^0$/);
});

test("sin pista no hay a dónde adelantar", async () => {
  render(<PlayerProvider><ShortcutProbe /></PlayerProvider>);
  await key("ArrowRight");
  expect(screen.getByTestId("position")).toHaveTextContent(/^0$/);
});

test("la tecla M silencia y vuelve a su volumen", async () => {
  await startShortcuts();
  const before = screen.getByTestId("volume").textContent;
  await key("KeyM");
  expect(screen.getByTestId("volume")).toHaveTextContent(/^0$/);
  await key("KeyM");
  expect(screen.getByTestId("volume").textContent).toBe(before);
});

function SleepProbe() {
  const { play, current, sleepTimer, setSleepTimer, notice } = usePlayer();
  return (
    <>
      <button type="button" onClick={() => play([second, third])}>Empezar</button>
      <button type="button" onClick={() => setSleepTimer({ minutes: 15 })}>15 min</button>
      <button type="button" onClick={() => setSleepTimer({ minutes: 30 })}>30 min</button>
      <button type="button" onClick={() => setSleepTimer("track")}>Al terminar</button>
      <button type="button" onClick={() => setSleepTimer(null)}>Quitar</button>
      <p data-testid="current">{current?.title}</p>
      <p data-testid="sleep">{sleepTimer ? sleepTimer.kind : "none"}</p>
      <p data-testid="notice">{notice}</p>
    </>
  );
}

async function startSleep() {
  render(<PlayerProvider><SleepProbe /></PlayerProvider>);
  await press("Empezar");
}

const minutes = (count: number) => act(async () => void vi.advanceTimersByTime(count * 60_000));

test("el temporizador pausa la música al cumplirse", async () => {
  await startSleep();
  vi.useFakeTimers({ shouldAdvanceTime: false });
  try {
    await press("15 min");
    expect(screen.getByTestId("sleep")).toHaveTextContent("minutes");
    await minutes(14);
    expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled();
    await minutes(1);
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();
    expect(screen.getByTestId("sleep")).toHaveTextContent("none");
    expect(screen.getByTestId("notice")).toHaveTextContent("La música se detuvo por el temporizador");
  } finally {
    vi.useRealTimers();
  }
});

test("un temporizador nuevo reemplaza al anterior", async () => {
  await startSleep();
  vi.useFakeTimers({ shouldAdvanceTime: false });
  try {
    await press("15 min");
    await press("30 min");
    await minutes(20);
    expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled();
    await minutes(10);
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalledOnce();
  } finally {
    vi.useRealTimers();
  }
});

test("quitar el temporizador lo cancela", async () => {
  await startSleep();
  vi.useFakeTimers({ shouldAdvanceTime: false });
  try {
    await press("15 min");
    await press("Quitar");
    expect(screen.getByTestId("sleep")).toHaveTextContent("none");
    await minutes(60);
    expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled();
  } finally {
    vi.useRealTimers();
  }
});

test("al terminar la pista, la música se detiene en lugar de pasar a la siguiente", async () => {
  await startSleep();
  await press("Al terminar");
  expect(screen.getByTestId("sleep")).toHaveTextContent("track");
  await act(async () => void fireEvent.ended(document.querySelector("audio")!));
  expect(screen.getByTestId("current")).toHaveTextContent("Segunda");
  expect(screen.getByTestId("sleep")).toHaveTextContent("none");
  expect(screen.getByTestId("notice")).toHaveTextContent("La música se detuvo por el temporizador");
});

test("sin temporizador, al terminar la pista pasa a la siguiente", async () => {
  await startSleep();
  await act(async () => void fireEvent.ended(document.querySelector("audio")!));
  await waitFor(() => expect(screen.getByTestId("current")).toHaveTextContent("Tercera"));
});

type SessionHandler = (details: { seekTime?: number; seekOffset?: number }) => void;

function fakeMediaSession() {
  const handlers: Record<string, SessionHandler> = {};
  const session = {
    metadata: null as unknown,
    playbackState: "none",
    setActionHandler: vi.fn((action: string, handler: SessionHandler | null) => {
      if (handler) handlers[action] = handler;
    }),
    setPositionState: vi.fn(),
  };
  vi.stubGlobal("MediaMetadata", class { constructor(public init: unknown) {} });
  Object.defineProperty(navigator, "mediaSession", { value: session, configurable: true });
  return { session, handlers };
}

const withMediaSession = async (check: (fake: ReturnType<typeof fakeMediaSession>) => Promise<void>) => {
  const fake = fakeMediaSession();
  try {
    await startShortcuts();
    await check(fake);
  } finally {
    Reflect.deleteProperty(navigator, "mediaSession");
  }
};

test("la pantalla de bloqueo puede saltar a un punto de la pista", () =>
  withMediaSession(async ({ handlers }) => {
    await act(async () => handlers.seekto({ seekTime: 42 }));
    expect(screen.getByTestId("position")).toHaveTextContent(/^42$/);
  }));

test("adelantar y retroceder usan el salto que pide el sistema, o 10 s", () =>
  withMediaSession(async ({ handlers }) => {
    await act(async () => handlers.seekforward({}));
    expect(screen.getByTestId("position")).toHaveTextContent(/^10$/);
    await act(async () => handlers.seekforward({ seekOffset: 30 }));
    expect(screen.getByTestId("position")).toHaveTextContent(/^40$/);
    await act(async () => handlers.seekbackward({}));
    expect(screen.getByTestId("position")).toHaveTextContent(/^30$/);
  }));

test("un seekto sin tiempo se ignora", () =>
  withMediaSession(async ({ handlers }) => {
    await act(async () => handlers.seekto({}));
    expect(screen.getByTestId("position")).toHaveTextContent(/^0$/);
  }));

test("el sistema recibe la posición y la duración de la pista", () =>
  withMediaSession(async ({ handlers, session }) => {
    await act(async () => handlers.seekto({ seekTime: 42 }));
    expect(session.setPositionState).toHaveBeenLastCalledWith({ duration: 183, playbackRate: 1, position: 42 });
  }));

test("el sistema sabe si suena o está en pausa", () =>
  withMediaSession(async ({ session }) => {
    expect(session.playbackState).toBe("paused");
    await act(async () => void fireEvent.play(document.querySelector("audio")!));
    expect(session.playbackState).toBe("playing");
  }));

test("una posición que el navegador rechaza no rompe el reproductor", () =>
  withMediaSession(async ({ handlers, session }) => {
    session.setPositionState.mockImplementation(() => {
      throw new TypeError("posición inválida");
    });
    await act(async () => handlers.seekto({ seekTime: 42 }));
    expect(screen.getByTestId("position")).toHaveTextContent(/^42$/);
  }));

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
