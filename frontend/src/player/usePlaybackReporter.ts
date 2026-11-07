import { useEffect, useRef } from "react";
import { api, ApiError } from "../api/client";

const KEY = "meloxo.pending-playbacks";
const THRESHOLD_SECONDS = 10;
const MAX_STEP_SECONDS = 2;
const FIRST_DELAY_MS = 1000;
const MAX_DELAY_MS = 60_000;

type Send = (path: string, options: { method: string; json: unknown }) => Promise<unknown>;

type Pending = {
  playback_id: string;
  song_id: string;
  listened_seconds: number;
  posted: boolean;
  sent_seconds: number;
};

type Current = { id: string; songId: string; listened: number; last: number | null; reported: boolean; posted: boolean };

function load(): Pending[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

/** Un 4xx no se arregla reintentando. La sesión vencida sí, cuando la persona vuelva a entrar. */
function isPermanent(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  return error.status >= 400 && error.status < 500 && ![401, 408, 429].includes(error.status);
}

/** Lleva la cuenta de lo escuchado de verdad. Nunca lanza: una métrica no debe cortar el audio (F3.3). */
export class PlaybackReporter {
  private pending: Pending[] = load();
  private current: Current | null = null;
  private delay = FIRST_DELAY_MS;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private flushing = false;
  private again = false;

  constructor(private readonly send: Send) {
    if (this.pending.length) void this.flush();
  }

  begin(songId: string): void {
    this.current = {
      id: crypto.randomUUID(),
      songId,
      listened: 0,
      last: null,
      reported: false,
      posted: false,
    };
  }

  /** Solo cuentan los avances pequeños: un salto grande es alguien adelantando. */
  progress(position: number): void {
    const current = this.current;
    if (!current) return;
    if (current.last !== null) {
      const step = position - current.last;
      if (step > 0 && step <= MAX_STEP_SECONDS) current.listened += step;
    }
    current.last = position;
    if (!current.reported && current.listened >= THRESHOLD_SECONDS) {
      current.reported = true;
      this.enqueue(current, THRESHOLD_SECONDS);
    }
  }

  pause(): void {
    if (this.current?.reported) this.enqueue(this.current, Math.round(this.current.listened));
  }

  end(): void {
    if (this.current?.reported) this.enqueue(this.current, Math.ceil(this.current.listened));
  }

  dispose(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }

  private enqueue(current: Current, seconds: number): void {
    const found = this.pending.find((entry) => entry.playback_id === current.id);
    if (found) {
      found.listened_seconds = Math.max(found.listened_seconds, seconds);
    } else {
      this.pending.push({
        playback_id: current.id,
        song_id: current.songId,
        listened_seconds: seconds,
        posted: current.posted,
        sent_seconds: current.posted ? THRESHOLD_SECONDS : 0,
      });
    }
    this.save();
    void this.flush();
  }

  private save(): void {
    try {
      localStorage.setItem(KEY, JSON.stringify(this.pending));
    } catch {
      // Sin almacenamiento el reintento vive solo en memoria.
    }
  }

  private async deliver(entry: Pending): Promise<void> {
    if (!entry.posted) {
      await this.send("/api/playbacks", {
        method: "POST",
        json: { playback_id: entry.playback_id, song_id: entry.song_id, listened_seconds: entry.listened_seconds },
      });
      entry.posted = true;
      entry.sent_seconds = entry.listened_seconds;
      if (this.current?.id === entry.playback_id) this.current.posted = true;
      this.save();
    }
    if (entry.listened_seconds > entry.sent_seconds) {
      const seconds = entry.listened_seconds;
      await this.send(`/api/playbacks/${entry.playback_id}/progress`, {
        method: "PATCH",
        json: { listened_seconds: seconds },
      });
      entry.sent_seconds = seconds;
    }
  }

  private async flush(): Promise<void> {
    if (this.flushing) {
      this.again = true;
      return;
    }
    this.flushing = true;
    let failed = false;
    for (const entry of [...this.pending]) {
      try {
        await this.deliver(entry);
        this.remove(entry);
      } catch (error) {
        if (isPermanent(error)) {
          this.remove(entry);
        } else {
          failed = true;
          break;
        }
      }
    }
    this.flushing = false;
    if (failed) {
      this.again = false;
      this.retryLater();
    } else {
      this.delay = FIRST_DELAY_MS;
      if (this.again) {
        this.again = false;
        void this.flush();
      }
    }
  }

  private remove(entry: Pending): void {
    if (entry.listened_seconds > entry.sent_seconds && entry.posted) return;
    this.pending = this.pending.filter((other) => other !== entry);
    this.save();
  }

  private retryLater(): void {
    if (this.timer) return;
    this.timer = setTimeout(() => {
      this.timer = null;
      void this.flush();
    }, this.delay);
    this.delay = Math.min(this.delay * 2, MAX_DELAY_MS);
  }
}

export function usePlaybackReporter(): PlaybackReporter {
  const reporter = useRef<PlaybackReporter | null>(null);
  reporter.current ??= new PlaybackReporter(api);
  useEffect(() => () => reporter.current?.dispose(), []);
  return reporter.current;
}
