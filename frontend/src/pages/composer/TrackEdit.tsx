import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import type { Track } from "./Tracks";

type Album = { id: string; title: string };

/** datetime-local trabaja en hora local y sin zona. */
function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function EditForm({ track }: { track: Track }) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const [title, setTitle] = useState(track.title);
  const [genre, setGenre] = useState(track.genres[0] ?? "");
  const [license, setLicense] = useState(track.license ?? "");
  const [albumId, setAlbumId] = useState(track.album_id ?? "");
  const originalDate = toLocalInput(track.publish_at);
  const [publishAt, setPublishAt] = useState(originalDate);
  const albums = useQuery({ queryKey: ["composer-albums"], queryFn: () => api<Album[]>("/api/composer/albums") });
  const schedulable = track.status === "draft" || track.status === "scheduled";

  const save = useMutation({
    mutationFn: () => {
      const json: Record<string, string | null> = { title, genre, license, album_id: albumId || null };
      if (publishAt !== originalDate) json.publish_at = publishAt ? new Date(publishAt).toISOString() : null;
      return api(`/api/composer/tracks/${track.id}`, { method: "PATCH", json });
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["composer-tracks"] });
      navigate("/composer");
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <form className="stack-form" onSubmit={submit}>
      <label>Título<input required maxLength={300} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
      <label>Género<input required maxLength={60} value={genre} onChange={(e) => setGenre(e.target.value)} /></label>
      <label>Licencia<input required maxLength={120} value={license} onChange={(e) => setLicense(e.target.value)} /></label>
      <label>
        Álbum o EP
        <select value={albumId} onChange={(e) => setAlbumId(e.target.value)}>
          <option value="">Sin álbum</option>
          {albums.data?.map((album) => <option key={album.id} value={album.id}>{album.title}</option>)}
        </select>
      </label>
      {schedulable && (
        <>
          <label>
            Fecha de publicación
            <input type="datetime-local" value={publishAt} onChange={(e) => setPublishAt(e.target.value)} />
          </label>
          <small>Sin fecha, la pista queda en borrador hasta que la publiques.</small>
        </>
      )}
      {save.error instanceof ApiError && <p className="form-error" role="alert">{save.error.message}</p>}
      <div className="row-actions">
        <button className="primary" type="submit" disabled={save.isPending}>Guardar cambios</button>
        <Link className="ghost" to="/composer">Cancelar</Link>
      </div>
    </form>
  );
}

export function TrackEdit() {
  const { id } = useParams();
  const tracks = useQuery({ queryKey: ["composer-tracks"], queryFn: () => api<Track[]>("/api/composer/tracks") });
  const track = tracks.data?.find((item) => item.id === id);
  return (
    <>
      <h1 className="page-title">Editar pista</h1>
      {tracks.isError && <p className="form-error" role="alert">{tracks.error.message}</p>}
      {tracks.isSuccess && !track && <p className="form-error" role="alert">No encontramos esta pista.</p>}
      {track && <EditForm key={track.id} track={track} />}
    </>
  );
}
