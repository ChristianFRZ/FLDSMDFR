import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Page, Song, TapeDetail as Detail, TapeTrack } from "../api/types";
import { DedicationEditor } from "../components/DedicationEditor";
import { Icon } from "../components/Icon";
import { InvitePanel } from "../components/InvitePanel";
import { Tape } from "../components/Tape";
import { TapeSide } from "../components/TapeSide";
import { usePlayer } from "../player/PlayerProvider";

function slotsLabel(free: number): string {
  if (free === 0) return "Casete lleno";
  return free === 1 ? "Queda 1 lugar" : `Quedan ${free} lugares`;
}

function addError(error: unknown): string {
  if (error instanceof ApiError && error.code === "tape_full") {
    return "Alguien ocupó el último lugar del casete. Ya no caben más pistas.";
  }
  return error instanceof ApiError ? error.message : "No se pudo agregar. Intenta de nuevo.";
}

function AddTrack({ tapeId, onDone, onError }: { tapeId: string; onDone: () => void; onError: (message: string) => void }) {
  const [text, setText] = useState("");
  const [chosen, setChosen] = useState<Song | null>(null);
  const [dedication, setDedication] = useState("");
  const results = useQuery({
    queryKey: ["tape-search", text],
    queryFn: () => api<Page<Song>>(`/api/songs?q=${encodeURIComponent(text)}&size=8`),
    enabled: text.trim().length >= 2,
  });
  const add = useMutation({
    mutationFn: () =>
      api(`/api/tapes/${tapeId}/tracks`, {
        method: "POST",
        json: { song_id: chosen?.id, dedication: dedication.trim() || null },
      }),
    onSuccess: onDone,
    onError: (error) => onError(addError(error)),
  });

  if (chosen) {
    return (
      <div className="add-track">
        <p>Agregar <b>{chosen.title}</b> de {chosen.artist}</p>
        <DedicationEditor value={dedication} onChange={setDedication} />
        <div className="sheet-actions">
          <button className="ghost" type="button" onClick={() => setChosen(null)}>Volver</button>
          <button className="primary" type="button" disabled={add.isPending} onClick={() => add.mutate()}>Agregar al casete</button>
        </div>
      </div>
    );
  }
  return (
    <div className="add-track">
      <input
        className="field"
        type="search"
        aria-label="Buscar pista para el casete"
        placeholder="Busca una canción o artista"
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <ul className="pick-list">
        {results.data?.items.map((song) => (
          <li key={song.id}>
            <button type="button" aria-label={`Elegir ${song.title}`} onClick={() => setChosen(song)}>
              <b>{song.title}</b>
              <small>{song.artist}</small>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Rename({ tape, onDone }: { tape: Detail; onDone: () => void }) {
  const [title, setTitle] = useState(tape.title);
  const save = useMutation({
    mutationFn: () => api(`/api/tapes/${tape.id}`, { method: "PATCH", json: { title } }),
    onSuccess: onDone,
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }
  return (
    <form className="inline-form" onSubmit={submit}>
      <input aria-label="Nombre del casete" required maxLength={80} value={title} onChange={(e) => setTitle(e.target.value)} />
      <button className="ghost" type="submit" disabled={save.isPending}>Guardar</button>
    </form>
  );
}

export function TapeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const { play } = usePlayer();
  const [adding, setAdding] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const key = ["tape", id];
  const query = useQuery({ queryKey: key, queryFn: () => api<Detail>(`/api/tapes/${id}`) });
  const refresh = () => {
    void client.invalidateQueries({ queryKey: key });
    void client.invalidateQueries({ queryKey: ["tapes"] });
  };

  const reorder = useMutation({
    mutationFn: (json: { version: number; track_ids: string[] }) =>
      api(`/api/tapes/${id}/order`, { method: "PUT", json }),
    onSuccess: () => {
      setProblem(null);
      refresh();
    },
    onError: (error) => {
      const conflict = error instanceof ApiError && error.code === "tape_version_conflict";
      setProblem(conflict ? "Alguien cambió el casete. Este es el orden nuevo." : error.message);
      refresh();
    },
  });

  const remove = useMutation({
    mutationFn: (trackId: string) => api(`/api/tapes/${id}/tracks/${trackId}`, { method: "DELETE" }),
    onSettled: refresh,
    onError: (error) => setProblem(error.message),
  });

  const destroy = useMutation({
    mutationFn: () => api(`/api/tapes/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["tapes"] });
      navigate("/library");
    },
  });

  if (query.isError) {
    const denied = query.error instanceof ApiError && query.error.status === 403;
    return (
      <p className="form-error" role="alert">
        {denied ? "Este casete es privado: necesitas una invitación para verlo." : query.error.message}
      </p>
    );
  }
  if (!query.data) return <p role="status">Cargando…</p>;

  const tape = query.data;
  const free = tape.max_tracks - tape.tracks.length;
  const half = Math.ceil(tape.max_tracks / 2);

  function start(track?: TapeTrack) {
    const songs = tape.tracks.map((t) => ({
      ...t.song,
      dedication: t.dedication,
      dedicatedBy: t.added_by_name,
      side: t.side,
    }));
    const context = { title: tape.title, color: tape.color, href: `/tapes/${tape.id}` };
    play(songs, track ? tape.tracks.indexOf(track) : 0, context);
  }

  function move(track: TapeTrack, to: number) {
    const ids = tape.tracks.map((t) => t.id).filter((other) => other !== track.id);
    ids.splice(to - 1, 0, track.id);
    reorder.mutate({ version: tape.version, track_ids: ids });
  }

  const shared = {
    total: tape.tracks.length,
    busy: reorder.isPending,
    onPlay: start,
    onMove: move,
    onRemove: (track: TapeTrack) => remove.mutate(track.id),
  };

  return (
    <div className="tape-page">
      <header className="tape-head">
        <Tape title={tape.title} color={tape.color} tilt={-3} />
        <div>
          {renaming ? (
            <Rename tape={tape} onDone={() => { setRenaming(false); refresh(); }} />
          ) : (
            <h1 className="page-title">{tape.title}</h1>
          )}
          <p className="muted">{tape.tracks.length} de {tape.max_tracks} pistas · <span>{slotsLabel(free)}</span></p>
          <div className="row-actions">
            <button className="primary" type="button" disabled={!tape.tracks.some((t) => t.song.available)} onClick={() => start()}>
              <Icon name="play" filled />Reproducir
            </button>
            <button className="ghost" type="button" disabled={free === 0} aria-expanded={adding} onClick={() => setAdding(!adding)}>
              <Icon name="plus" />Agregar pista
            </button>
            {tape.is_creator && (
              <button className="ghost" type="button" onClick={() => setRenaming(!renaming)}>Renombrar</button>
            )}
          </div>
        </div>
      </header>

      {tape.degraded && <p className="banner" role="status">El catálogo no responde. Te mostramos los datos guardados.</p>}
      {problem && <p className="form-error" role="alert">{problem}</p>}
      {adding && free > 0 && (
        <AddTrack
          tapeId={tape.id}
          onDone={() => { setAdding(false); setProblem(null); refresh(); }}
          onError={(message) => { setProblem(message); refresh(); }}
        />
      )}

      <div className="tape-sides">
        <TapeSide side="A" tracks={tape.tracks.filter((t) => t.position <= half)} {...shared} />
        <TapeSide side="B" tracks={tape.tracks.filter((t) => t.position > half)} {...shared} />
      </div>

      <InvitePanel tape={tape} />

      {tape.is_creator && (
        <div className="row-actions">
          {confirming ? (
            <>
              <span>Se borra para todos los miembros, con sus dedicatorias.</span>
              <button className="ghost danger" type="button" onClick={() => destroy.mutate()}>Sí, eliminar</button>
              <button className="ghost" type="button" onClick={() => setConfirming(false)}>Cancelar</button>
            </>
          ) : (
            <button className="ghost" type="button" onClick={() => setConfirming(true)}>Eliminar casete</button>
          )}
        </div>
      )}
      <p className="muted"><Link to="/library">Volver a tu biblioteca</Link></p>
    </div>
  );
}
