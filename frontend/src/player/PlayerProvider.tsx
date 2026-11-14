import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { Song } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import type { TapeColor } from "../components/Tape";
import * as Q from "./queue";
import { recoverStream, streamUrl } from "./recovery";
import { usePlaybackReporter } from "./usePlaybackReporter";

export type QueueSong = Song & { dedication?: string | null; dedicatedBy?: string | null; side?: string };
export type PlayContext = { title: string; color: TapeColor; href: string };
/** `endsAt` es la hora (ms) en que se detiene. "track" espera a que termine la pista que suena. */
export type SleepTimer = { kind: "minutes"; endsAt: number } | { kind: "track" };
export type SleepOption = { minutes: number } | "track" | null;

const VOLUME_KEY = "meloxo.volume";
const MAX_RECOVERIES = 2;

type Player = {
  current: QueueSong | undefined;
  queue: QueueSong[];
  context: PlayContext | null;
  isPlaying: boolean;
  position: number;
  duration: number;
  volume: number;
  shuffle: boolean;
  repeat: Q.Repeat;
  notice: string | null;
  sleepTimer: SleepTimer | null;
  play: (songs: QueueSong[], startIndex?: number, context?: PlayContext | null) => void;
  toggle: () => void;
  next: () => void;
  prev: () => void;
  seek: (seconds: number) => void;
  jump: (offset: number) => void;
  playNext: (song: QueueSong) => void;
  addToQueue: (song: QueueSong) => void;
  removeFromQueue: (offset: number) => void;
  moveInQueue: (from: number, to: number) => void;
  setVolume: (value: number) => void;
  toggleMute: () => void;
  setSleepTimer: (option: SleepOption) => void;
  setShuffle: (value: boolean) => void;
  setRepeat: (value: Q.Repeat) => void;
  dismissNotice: () => void;
};

const PlayerContext = createContext<Player | null>(null);

function readVolume(): number {
  try {
    const stored = Number(localStorage.getItem(VOLUME_KEY));
    return stored > 0 && stored <= 1 ? stored : 0.8;
  } catch {
    return 0.8;
  }
}

const requestTicket = async (songId: string) =>
  (await api<{ ticket: string }>(`/api/songs/${songId}/stream-ticket`, { method: "POST" })).ticket;

async function probe(src: string): Promise<number> {
  const response = await fetch(src, { headers: { range: "bytes=0-0" } });
  await response.body?.cancel();
  return response.status;
}

const isTyping = (target: EventTarget | null) =>
  target instanceof HTMLElement && target.closest("input, textarea, select, button, a, [contenteditable]") !== null;

/** Las flechas las usan los campos y los deslizadores: ahí no son un atajo. */
const isEditing = (target: EventTarget | null) =>
  target instanceof HTMLElement && target.closest("input, textarea, select, [contenteditable]") !== null;

const SEEK_STEP = 5;
const MEDIA_SEEK_STEP = 10;

export function PlayerProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const reporter = usePlaybackReporter();
  const audio = useRef<HTMLAudioElement>(null);
  const [queue, setQueue] = useState<Q.Queue<QueueSong>>(Q.createQueue([], 0, { shuffle: false, repeat: "off" }));
  const [context, setContext] = useState<PlayContext | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(readVolume);
  const [notice, setNotice] = useState<string | null>(null);
  const [sleepTimer, setSleepTimerState] = useState<SleepTimer | null>(null);
  const sleepRef = useRef(sleepTimer);
  sleepRef.current = sleepTimer;
  const sleepHandle = useRef<ReturnType<typeof setTimeout>>();
  const queueRef = useRef(queue);
  queueRef.current = queue;
  const recoveries = useRef(0);
  const resumeAt = useRef<number | null>(null);
  const recovering = useRef<string | null>(null);

  const current = Q.currentItem(queue);

  const start = useCallback(
    async (song: QueueSong) => {
      const element = audio.current;
      if (!element) return;
      reporter.begin(song.id);
      recoveries.current = 0;
      resumeAt.current = null;
      setPosition(0);
      setDuration(song.duration || 0);
      try {
        element.src = streamUrl(song.id, await requestTicket(song.id));
      } catch {
        element.dispatchEvent(new Event("error"));
        return;
      }
      try {
        await element.play();
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (error instanceof DOMException && error.name === "NotAllowedError") return;
        // Si la fuente falló, el elemento ya lanza su propio error: un segundo saltaría otra pista.
        if (!element.error) element.dispatchEvent(new Event("error"));
      }
    },
    [reporter],
  );

  const advance = useCallback(
    (auto: boolean) => {
      const element = audio.current;
      const step = Q.next(queueRef.current, auto);
      if (auto) reporter.end();
      else reporter.pause();
      if (step.ended) {
        element?.pause();
        return;
      }
      setQueue(step.queue);
      const song = Q.currentItem(step.queue);
      if (step.restart && element) {
        reporter.begin(song!.id);
        element.currentTime = 0;
        void element.play();
      } else if (song) {
        void start(song);
      }
    },
    [reporter, start],
  );

  const play = useCallback<Player["play"]>(
    (songs, startIndex = 0, nextContext = null) => {
      const playable = songs.filter((song) => song.available);
      const chosen = songs[startIndex];
      const index = Math.max(0, playable.indexOf(chosen));
      if (!playable.length) {
        setNotice("Esta pista ya no está disponible.");
        return;
      }
      reporter.pause();
      const { shuffle, repeat } = queueRef.current;
      const created = Q.createQueue(playable, index, { shuffle, repeat });
      setQueue(created);
      setContext(nextContext);
      setNotice(null);
      void start(Q.currentItem(created)!);
    },
    [reporter, start],
  );

  const toggle = useCallback(() => {
    const element = audio.current;
    if (!element || !Q.currentItem(queueRef.current)) return;
    if (element.paused) void element.play().catch(() => undefined);
    else element.pause();
  }, []);

  const prev = useCallback(() => {
    const element = audio.current;
    const step = Q.prev(queueRef.current, element?.currentTime ?? 0);
    if (step.restart) {
      if (element) element.currentTime = 0;
      return;
    }
    reporter.pause();
    setQueue(step.queue);
    void start(Q.currentItem(step.queue)!);
  }, [reporter, start]);

  const seek = useCallback((seconds: number) => {
    if (audio.current) audio.current.currentTime = seconds;
    setPosition(seconds);
  }, []);

  const jump = useCallback(
    (offset: number) => {
      reporter.pause();
      const moved = Q.jumpTo(queueRef.current, offset);
      setQueue(moved);
      void start(Q.currentItem(moved)!);
    },
    [reporter, start],
  );

  /** Con la cola vacía no hay "a continuación": la pista simplemente suena. */
  const enqueue = useCallback(
    (song: QueueSong, place: typeof Q.enqueueNext, notice: string) => {
      if (!song.available) {
        setNotice("Esta pista ya no está disponible.");
        return;
      }
      if (!Q.currentItem(queueRef.current)) {
        play([song]);
        return;
      }
      setQueue((q) => place(q, song));
      setNotice(notice);
    },
    [play],
  );

  const playNext = useCallback(
    (song: QueueSong) => enqueue(song, Q.enqueueNext, `«${song.title}» sonará a continuación.`),
    [enqueue],
  );

  const addToQueue = useCallback(
    (song: QueueSong) => enqueue(song, Q.enqueueLast, `«${song.title}» se agregó a la cola.`),
    [enqueue],
  );

  const removeFromQueue = useCallback((offset: number) => setQueue((q) => Q.removeUpcoming(q, offset)), []);

  const moveInQueue = useCallback((from: number, to: number) => setQueue((q) => Q.moveUpcoming(q, from, to)), []);

  const setVolume = useCallback((value: number) => {
    setVolumeState(value);
    try {
      localStorage.setItem(VOLUME_KEY, String(value));
    } catch {
      // El volumen simplemente no se recuerda.
    }
  }, []);

  const stopForSleep = useCallback(() => {
    setSleepTimerState(null);
    setNotice("La música se detuvo por el temporizador.");
  }, []);

  const setSleepTimer = useCallback(
    (option: SleepOption) => {
      clearTimeout(sleepHandle.current);
      if (!option) {
        setSleepTimerState(null);
      } else if (option === "track") {
        setSleepTimerState({ kind: "track" });
      } else {
        const wait = option.minutes * 60_000;
        setSleepTimerState({ kind: "minutes", endsAt: Date.now() + wait });
        sleepHandle.current = setTimeout(() => {
          audio.current?.pause();
          stopForSleep();
        }, wait);
      }
    },
    [stopForSleep],
  );

  useEffect(() => () => clearTimeout(sleepHandle.current), []);

  const volumeRef = useRef(volume);
  volumeRef.current = volume;
  const lastVolume = useRef(volume || 0.8);

  const toggleMute = useCallback(() => {
    if (volumeRef.current > 0) {
      lastVolume.current = volumeRef.current;
      setVolume(0);
    } else {
      setVolume(lastVolume.current);
    }
  }, [setVolume]);

  const clock = useRef({ position, duration });
  clock.current = { position, duration };

  /** Busca a `to` sin salirse de la pista. */
  const seekWithin = useCallback(
    (to: number) => {
      const total = clock.current.duration;
      seek(Math.max(0, total ? Math.min(total, to) : to));
    },
    [seek],
  );

  const onError = useCallback(async () => {
    const element = audio.current;
    const song = Q.currentItem(queueRef.current);
    if (!element || !song || recovering.current === song.id) return;
    recovering.current = song.id;
    try {
      recoveries.current += 1;
      if (recoveries.current > MAX_RECOVERIES) {
        setNotice("No pudimos reproducir esta pista. Pasamos a la siguiente.");
        advance(false);
        return;
      }
      const at = resumeAt.current ?? element.currentTime;
      const result = await recoverStream({ songId: song.id, position: at, requestTicket, probe });
      if (Q.currentItem(queueRef.current)?.id !== song.id) return; // Ya se pasó a otra pista.
      if (result.action === "resume") {
        resumeAt.current = result.position;
        element.src = result.src;
        void element.play().catch(() => undefined);
      } else if (result.action === "skip") {
        setNotice(result.notice);
        advance(false);
      } else {
        setNotice(result.notice);
        setIsPlaying(false);
      }
    } finally {
      if (recovering.current === song.id) recovering.current = null;
    }
  }, [advance]);

  useEffect(() => {
    if (audio.current) audio.current.volume = volume;
  }, [volume]);

  useEffect(() => {
    if (!user) {
      audio.current?.pause();
      audio.current?.removeAttribute("src");
      setQueue(Q.createQueue([], 0, { shuffle: false, repeat: "off" }));
      setContext(null);
    }
  }, [user]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.code === "Space" && !isTyping(event.target)) {
        event.preventDefault();
        toggle();
        return;
      }
      // Alt+← es "atrás" del navegador, y Ctrl o Cmd con letras son suyos.
      if (event.altKey || event.ctrlKey || event.metaKey || isEditing(event.target)) return;
      if (!Q.currentItem(queueRef.current)) return;
      if (event.code === "ArrowRight" || event.code === "ArrowLeft") {
        event.preventDefault();
        seekWithin(clock.current.position + (event.code === "ArrowRight" ? SEEK_STEP : -SEEK_STEP));
      } else if (event.code === "KeyM") {
        toggleMute();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle, seekWithin, toggleMute]);

  useEffect(() => {
    if (!("mediaSession" in navigator) || !current) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: current.title,
      artist: current.artist,
      album: current.album ?? undefined,
      artwork: current.cover_url ? [{ src: current.cover_url }] : [],
    });
    navigator.mediaSession.setActionHandler("play", toggle);
    navigator.mediaSession.setActionHandler("pause", toggle);
    navigator.mediaSession.setActionHandler("nexttrack", () => advance(false));
    navigator.mediaSession.setActionHandler("previoustrack", prev);
  }, [current, toggle, advance, prev]);

  // La pantalla de bloqueo y las teclas multimedia también buscan dentro de la pista.
  useEffect(() => {
    if (!("mediaSession" in navigator) || !current) return;
    const session = navigator.mediaSession;
    session.setActionHandler("seekto", (details) => {
      if (typeof details.seekTime === "number") seekWithin(details.seekTime);
    });
    session.setActionHandler("seekforward", (details) =>
      seekWithin(clock.current.position + (details.seekOffset ?? MEDIA_SEEK_STEP)),
    );
    session.setActionHandler("seekbackward", (details) =>
      seekWithin(clock.current.position - (details.seekOffset ?? MEDIA_SEEK_STEP)),
    );
  }, [current, seekWithin]);

  useEffect(() => {
    if (!("mediaSession" in navigator)) return;
    navigator.mediaSession.playbackState = current ? (isPlaying ? "playing" : "paused") : "none";
  }, [current, isPlaying]);

  useEffect(() => {
    if (!("mediaSession" in navigator) || !current || !duration) return;
    try {
      navigator.mediaSession.setPositionState({ duration, playbackRate: 1, position: Math.min(position, duration) });
    } catch {
      // El navegador rechaza posiciones que no le cuadran: la barra del sistema solo queda sin actualizar.
    }
  }, [current, position, duration]);

  const value = useMemo<Player>(
    () => ({
      current,
      queue: Q.upcoming(queue),
      context,
      isPlaying,
      position,
      duration,
      volume,
      shuffle: queue.shuffle,
      repeat: queue.repeat,
      notice,
      sleepTimer,
      play,
      toggle,
      next: () => advance(false),
      prev,
      seek,
      jump,
      playNext,
      addToQueue,
      removeFromQueue,
      moveInQueue,
      setVolume,
      toggleMute,
      setSleepTimer,
      setShuffle: (next) => setQueue((q) => Q.setShuffle(q, next)),
      setRepeat: (next) => setQueue((q) => Q.setRepeat(q, next)),
      dismissNotice: () => setNotice(null),
    }),
    [current, queue, context, isPlaying, position, duration, volume, notice, sleepTimer, play, toggle, advance, prev, seek, jump, playNext, addToQueue, removeFromQueue, moveInQueue, setVolume, toggleMute, setSleepTimer],
  );

  return (
    <PlayerContext.Provider value={value}>
      {children}
      <audio
        ref={audio}
        preload="metadata"
        onPlay={() => setIsPlaying(true)}
        onPause={() => {
          setIsPlaying(false);
          reporter.pause();
        }}
        onEnded={() => {
          if (sleepRef.current?.kind === "track") {
            reporter.end();
            stopForSleep();
            return;
          }
          advance(true);
        }}
        onError={() => void onError()}
        onLoadedMetadata={(event) => {
          const element = event.currentTarget;
          if (Number.isFinite(element.duration)) setDuration(element.duration);
          if (resumeAt.current !== null) {
            element.currentTime = resumeAt.current;
            resumeAt.current = null;
          }
        }}
        onTimeUpdate={(event) => {
          const time = event.currentTarget.currentTime;
          setPosition(time);
          reporter.progress(time);
          if (recoveries.current && time > 0) recoveries.current = 0;
        }}
      />
    </PlayerContext.Provider>
  );
}

export function usePlayer(): Player {
  const player = useContext(PlayerContext);
  if (!player) throw new Error("usePlayer necesita PlayerProvider");
  return player;
}
