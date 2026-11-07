import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { PlaylistDetail } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { SongRow } from "../components/SongRow";
import { usePlayer } from "../player/PlayerProvider";

export function Playlist() {
  const { id } = useParams();
  const { user } = useAuth();
  const { play } = usePlayer();
  const navigate = useNavigate();
  const client = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const key = ["playlist", id];
  const playlist = useQuery({ queryKey: key, queryFn: () => api<PlaylistDetail>(`/api/playlists/${id}`) });
  const refresh = () => void client.invalidateQueries({ queryKey: key });

  const remove = useMutation({
    mutationFn: (songId: string) => api(`/api/playlists/${id}/songs/${songId}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
  const update = useMutation({
    mutationFn: (json: { is_public: boolean }) => api(`/api/playlists/${id}`, { method: "PATCH", json }),
    onSuccess: refresh,
  });
  const destroy = useMutation({
    mutationFn: () => api(`/api/playlists/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["playlists"] });
      navigate("/library");
    },
  });

  if (playlist.isError) {
    const denied = playlist.error instanceof ApiError && playlist.error.status === 403;
    return <p className="form-error" role="alert">{denied ? "Esta playlist es privada." : playlist.error.message}</p>;
  }
  if (!playlist.data) return <p role="status">Cargando…</p>;
  const { name, songs, degraded, owner_id, is_public } = playlist.data;
  const mine = owner_id === user?.id;

  return (
    <>
      <h1 className="page-title">{name}</h1>
      <p className="muted">{songs.length === 1 ? "1 pista" : `${songs.length} pistas`} · {is_public ? "Pública" : "Privada"}</p>
      {degraded && <p className="banner" role="status">El catálogo no responde. Te mostramos los datos guardados.</p>}
      <div className="row-actions">
        <button className="primary" type="button" disabled={!songs.some((s) => s.available)} onClick={() => play(songs, 0)}>
          <Icon name="play" filled />Reproducir
        </button>
        {mine && (
          <>
            <button className="ghost" type="button" onClick={() => update.mutate({ is_public: !is_public })}>
              {is_public ? "Hacer privada" : "Hacer pública"}
            </button>
            {confirming ? (
              <>
                <button className="ghost danger" type="button" onClick={() => destroy.mutate()}>Sí, eliminar</button>
                <button className="ghost" type="button" onClick={() => setConfirming(false)}>Cancelar</button>
              </>
            ) : (
              <button className="ghost" type="button" onClick={() => setConfirming(true)}>Eliminar playlist</button>
            )}
          </>
        )}
      </div>
      {songs.length ? (
        <ul className="songs">
          {songs.map((song, index) => (
            <SongRow
              key={song.id}
              song={song}
              onPlay={() => play(songs, index)}
              actions={
                mine && (
                  <button className="plain" type="button" aria-label={`Quitar ${song.title}`} onClick={() => remove.mutate(song.id)}>
                    <Icon name="trash" />
                  </button>
                )
              }
            />
          ))}
        </ul>
      ) : (
        <p className="muted">Busca una canción y agrégala con el botón +.</p>
      )}
    </>
  );
}
