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
  play: (songs: QueueSong[], startIndex?: number, context?: PlayContext | null) => void;
  toggle: () => void;
  next: () => void;
  prev: () => void;
  seek: (seconds: number) => void;
  jump: (offset: number) => void;
  setVolume: (value: number) => void;
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

  const setVolume = useCallback((value: number) => {
    setVolumeState(value);
    try {
      localStorage.setItem(VOLUME_KEY, String(value));
    } catch {
      // El volumen simplemente no se recuerda.
    }
  }, []);

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
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

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
      play,
      toggle,
      next: () => advance(false),
      prev,
      seek,
      jump,
      setVolume,
      setShuffle: (next) => setQueue((q) => Q.setShuffle(q, next)),
      setRepeat: (next) => setQueue((q) => Q.setRepeat(q, next)),
      dismissNotice: () => setNotice(null),
    }),
    [current, queue, context, isPlaying, position, duration, volume, notice, play, toggle, advance, prev, seek, jump, setVolume],
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
        onEnded={() => advance(true)}
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
