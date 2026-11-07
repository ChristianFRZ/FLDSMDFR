import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import type { Song } from "../../api/types";
import { Cover } from "../../components/Cover";
import { Icon } from "../../components/Icon";

export type Track = Song & {
  album_id: string | null;
  publish_at: string | null;
  hidden_by_admin: boolean;
  hidden_reason: string | null;
};

const dateFormat = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });

function statusLabel(track: Track): string {
  if (track.hidden_by_admin) return `Oculta por administración${track.hidden_reason ? `: ${track.hidden_reason}` : ""}`;
  if (track.status === "scheduled" && track.publish_at) return `Programada: ${dateFormat.format(new Date(track.publish_at))}`;
  return { draft: "Borrador", published: "Publicada", hidden: "Oculta" }[track.status] ?? track.status;
}

function Row({ track, onError }: { track: Track; onError: (message: string) => void }) {
  const client = useQueryClient();
  const [asking, setAsking] = useState(false);
  const act = useMutation({
    mutationFn: (action: "publish" | "hide" | "delete") =>
      action === "delete"
        ? api(`/api/composer/tracks/${track.id}`, { method: "DELETE" })
        : api(`/api/composer/tracks/${track.id}/${action}`, { method: "POST" }),
    onSettled: () => void client.invalidateQueries({ queryKey: ["composer-tracks"] }),
    onError: (error) => onError(error instanceof ApiError ? error.message : "No se pudo. Intenta de nuevo."),
  });
  return (
    <li className="song">
      <Cover id={track.id} url={track.cover_url} className="cover-row" />
      <div className="song-text">
        <b>{track.title}</b>
        <small>{statusLabel(track)}</small>
      </div>
      {!track.hidden_by_admin && track.status !== "published" && (
        <button className="ghost" type="button" disabled={act.isPending} onClick={() => act.mutate("publish")}>Publicar</button>
      )}
      {track.status === "published" && (
        <button className="ghost" type="button" disabled={act.isPending} onClick={() => act.mutate("hide")}>Ocultar</button>
      )}
      <Link className="ghost" to={`/composer/tracks/${track.id}`} aria-label={`Editar ${track.title}`}>Editar</Link>
      {asking ? (
        <span className="confirm">
          <button className="ghost danger" type="button" onClick={() => act.mutate("delete")}>Eliminar</button>
          <button className="ghost" type="button" onClick={() => setAsking(false)}>No</button>
        </span>
      ) : (
        <button className="plain" type="button" aria-label={`Eliminar ${track.title}`} onClick={() => setAsking(true)}>
          <Icon name="trash" />
        </button>
      )}
    </li>
  );
}

export function Tracks() {
  const [problem, setProblem] = useState<string | null>(null);
  const tracks = useQuery({ queryKey: ["composer-tracks"], queryFn: () => api<Track[]>("/api/composer/tracks") });
  return (
    <>
      <h1 className="page-title">Tu música</h1>
      <div className="row-actions">
        <Link className="primary" to="/composer/new"><Icon name="upload" />Subir pista</Link>
        <Link className="ghost" to="/composer/albums">Álbumes y EP</Link>
        <Link className="ghost" to="/composer/profile">Perfil de artista</Link>
        <Link className="ghost" to="/composer/stats">Estadísticas</Link>
      </div>
      {problem && <p className="form-error" role="alert">{problem}</p>}
      {tracks.isSuccess && !tracks.data.length && <p className="muted">Aún no subes pistas. Empieza con la primera.</p>}
      <ul className="songs manage">
        {tracks.data?.map((track) => <Row key={track.id} track={track} onError={setProblem} />)}
      </ul>
    </>
  );
}
