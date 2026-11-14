import { useEffect, useRef, useState } from "react";
import type { Song } from "../api/types";
import { usePlayer } from "../player/PlayerProvider";
import { Icon } from "./Icon";

/** Acciones de cola de una pista. "Agregar a un casete o playlist" sigue aparte, con su propio botón. */
export function SongMenu({ song }: { song: Song }) {
  const { playNext, addToQueue } = usePlayer();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: Event) => {
      if (event instanceof KeyboardEvent) {
        if (event.key !== "Escape") return;
        setOpen(false);
        opener.current?.focus();
      } else if (!root.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const choose = (action: (chosen: Song) => void) => {
    setOpen(false);
    action(song);
  };

  return (
    <div className="menu" ref={root}>
      <button
        ref={opener}
        className="plain"
        type="button"
        aria-label={`Más acciones de ${song.title}`}
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <Icon name="more" />
      </button>
      {open && (
        <div className="menu-body" role="group" aria-label={`Acciones de ${song.title}`}>
          <button type="button" onClick={() => choose(playNext)}>Reproducir siguiente</button>
          <button type="button" onClick={() => choose(addToQueue)}>Agregar a la cola</button>
        </div>
      )}
    </div>
  );
}
