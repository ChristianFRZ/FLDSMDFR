import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { usePlaylists, useTapes } from "../api/queries";
import type { Song } from "../api/types";
import { DedicationEditor } from "./DedicationEditor";
import { Icon } from "./Icon";
import { tapeHex } from "./tapeColors";

type Target = { kind: "tape" | "playlist"; id: string; title: string };

const AddSongContext = createContext<(song: Song) => void>(() => undefined);

export const useAddSong = () => useContext(AddSongContext);

function AddSongDialog({ song, onClose }: { song: Song; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const client = useQueryClient();
  const tapes = useTapes();
  const playlists = usePlaylists();
  const [target, setTarget] = useState<Target | null>(null);
  const [dedication, setDedication] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    dialog.current?.showModal?.();
  }, []);

  const add = useMutation({
    mutationFn: (chosen: Target) =>
      chosen.kind === "tape"
        ? api(`/api/tapes/${chosen.id}/tracks`, {
            method: "POST",
            json: { song_id: song.id, dedication: dedication.trim() || null },
          })
        : api(`/api/playlists/${chosen.id}/songs`, { method: "POST", json: { song_id: song.id } }),
    onSuccess: (_, chosen) => {
      void client.invalidateQueries({ queryKey: ["tapes"] });
      void client.invalidateQueries({ queryKey: [chosen.kind, chosen.id] });
      onClose();
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : "No se pudo agregar. Intenta de nuevo."),
  });

  return (
    <dialog ref={dialog} className="sheet" aria-label={`Agregar ${song.title}`} onClose={onClose}>
      <header className="sheet-head">
        <h2>Agregar «{song.title}»</h2>
        <button className="plain" type="button" aria-label="Cerrar" onClick={onClose}><Icon name="close" /></button>
      </header>
      {target?.kind === "tape" ? (
        <>
          <p>Al casete <b>{target.title}</b></p>
          <DedicationEditor value={dedication} onChange={setDedication} />
          {message && <p className="form-error" role="alert">{message}</p>}
          <div className="sheet-actions">
            <button className="ghost" type="button" onClick={() => setTarget(null)}>Volver</button>
            <button className="primary" type="button" disabled={add.isPending} onClick={() => add.mutate(target)}>
              Agregar al casete
            </button>
          </div>
        </>
      ) : (
        <>
          {message && <p className="form-error" role="alert">{message}</p>}
          <h3>Casetes</h3>
          {tapes.data?.length ? (
            <ul className="pick-list">
              {tapes.data.map((tape) => {
                const full = tape.track_count >= tape.max_tracks;
                return (
                  <li key={tape.id}>
                    <button
                      type="button"
                      disabled={full}
                      onClick={() => setTarget({ kind: "tape", id: tape.id, title: tape.title })}
                    >
                      <span className="swatch" style={{ background: tapeHex(tape.color) }} />
                      <b>{tape.title}</b>
                      <small>{full ? "Lleno" : `${tape.track_count} de ${tape.max_tracks}`}</small>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="muted">Aún no tienes casetes. <Link to="/tapes/new" onClick={onClose}>Crea uno</Link></p>
          )}
          <h3>Playlists</h3>
          {playlists.data?.length ? (
            <ul className="pick-list">
              {playlists.data.map((playlist) => (
                <li key={playlist.id}>
                  <button
                    type="button"
                    disabled={add.isPending}
                    onClick={() => add.mutate({ kind: "playlist", id: playlist.id, title: playlist.name })}
                  >
                    <span className="swatch swatch-paper" />
                    <b>{playlist.name}</b>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Aún no tienes playlists.</p>
          )}
        </>
      )}
    </dialog>
  );
}

export function AddSongProvider({ children }: { children: ReactNode }) {
  const [song, setSong] = useState<Song | null>(null);
  const open = useCallback((chosen: Song) => setSong(chosen), []);
  const close = useCallback(() => setSong(null), []);
  const value = useMemo(() => open, [open]);
  return (
    <AddSongContext.Provider value={value}>
      {children}
      {song && <AddSongDialog song={song} onClose={close} />}
    </AddSongContext.Provider>
  );
}
