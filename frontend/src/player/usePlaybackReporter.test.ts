import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ApiError } from "../api/client";
import { PlaybackReporter } from "./usePlaybackReporter";

const KEY = "meloxo.pending-playbacks";

function play(reporter: PlaybackReporter, from: number, to: number) {
  for (let t = from; t <= to; t += 0.25) reporter.progress(t);
}

describe("reporte de reproducción", () => {
  let send: ReturnType<typeof vi.fn>;
  let reporter: PlaybackReporter;

  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    send = vi.fn().mockResolvedValue({});
    reporter = new PlaybackReporter(send);
    reporter.begin("cancion");
  });

  afterEach(() => {
    reporter.dispose();
    vi.useRealTimers();
  });

  const settle = () => vi.advanceTimersByTimeAsync(0);
  const posts = () => send.mock.calls.filter((c) => c[0] === "/api/playbacks");
  const patches = () => send.mock.calls.filter((c) => String(c[0]).endsWith("/progress"));

  test("no envía nada antes de 10 s", async () => {
    play(reporter, 0, 9.5);
    await settle();
    expect(send).not.toHaveBeenCalled();
  });

  test("envía POST /playbacks una vez a los 10 s reales", async () => {
    play(reporter, 0, 30);
    await settle();
    expect(posts()).toHaveLength(1);
    const body = posts()[0][1].json;
    expect(body.song_id).toBe("cancion");
    expect(body.listened_seconds).toBe(10);
    expect(body.playback_id).toMatch(/[0-9a-f-]{36}/);
  });

  test("adelantar no cuenta como escuchar", async () => {
    reporter.progress(0);
    reporter.progress(120);
    reporter.progress(120.25);
    await settle();
    expect(send).not.toHaveBeenCalled();
  });

  test("cada pista nueva tiene su propio playback_id", async () => {
    play(reporter, 0, 11);
    reporter.begin("otra");
    play(reporter, 0, 11);
    await settle();
    expect(posts()).toHaveLength(2);
    expect(posts()[0][1].json.playback_id).not.toBe(posts()[1][1].json.playback_id);
  });

  test("reintenta el evento con backoff si falla", async () => {
    send.mockRejectedValueOnce(new ApiError(503, "x", "x")).mockRejectedValueOnce(new ApiError(0, "network_error", "x"));
    play(reporter, 0, 11);
    await settle();
    expect(posts()).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(1000);
    expect(posts()).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(1000);
    expect(posts()).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(1000);
    expect(posts()).toHaveLength(3);
  });

  test("un fallo nunca sale hacia el reproductor", async () => {
    send.mockRejectedValue(new ApiError(503, "x", "x"));
    expect(() => play(reporter, 0, 11)).not.toThrow();
    await settle();
  });

  test("guarda eventos pendientes en localStorage y los reenvía", async () => {
    send.mockRejectedValue(new ApiError(503, "x", "x"));
    play(reporter, 0, 11);
    await settle();
    const saved = JSON.parse(localStorage.getItem(KEY)!);
    expect(saved).toHaveLength(1);
    reporter.dispose();

    const later = vi.fn().mockResolvedValue({});
    reporter = new PlaybackReporter(later);
    await settle();
    expect(later.mock.calls[0][0]).toBe("/api/playbacks");
    expect(later.mock.calls[0][1].json.playback_id).toBe(saved[0].playback_id);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual([]);
  });

  test("descarta un evento que el servidor rechaza para siempre", async () => {
    send.mockRejectedValueOnce(new ApiError(404, "song_not_found", "x"));
    play(reporter, 0, 11);
    await settle();
    await vi.advanceTimersByTimeAsync(5000);
    expect(posts()).toHaveLength(1);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual([]);
  });

  test("envía progreso al pausar", async () => {
    play(reporter, 0, 20);
    await settle();
    reporter.pause();
    await settle();
    expect(patches()).toHaveLength(1);
    expect(patches()[0][1].json.listened_seconds).toBe(20);
  });

  test("envía progreso al terminar, redondeando hacia arriba", async () => {
    play(reporter, 0, 20);
    reporter.progress(20.1);
    await settle();
    reporter.end();
    await settle();
    expect(patches()[0][1].json.listened_seconds).toBe(21);
  });

  test("pausar antes de 10 s no envía nada", async () => {
    play(reporter, 0, 5);
    reporter.pause();
    await settle();
    expect(send).not.toHaveBeenCalled();
  });

  test("si el POST falló, el reintento lleva el progreso más nuevo", async () => {
    send.mockRejectedValueOnce(new ApiError(503, "x", "x"));
    play(reporter, 0, 12);
    await settle();
    reporter.pause();
    await settle();
    expect(patches()).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(1000);
    expect(posts()).toHaveLength(2);
    expect(posts()[1][1].json.listened_seconds).toBe(12);
    expect(patches()).toHaveLength(0);
  });
});
