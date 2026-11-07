import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Artist as ArtistData, Song } from "../api/types";
import { ArtistLinks } from "../components/ArtistLinks";
import { SongRow } from "../components/SongRow";
import { usePlayer } from "../player/PlayerProvider";

export function Artist() {
  const { id } = useParams();
  const { play } = usePlayer();
  const client = useQueryClient();
  const artist = useQuery({
    queryKey: ["artist", id],
    queryFn: () => api<ArtistData & { songs: Song[] }>(`/api/artists/${id}`),
  });
  const followed = useQuery({ queryKey: ["follow-ids"], queryFn: () => api<string[]>("/api/follows/ids") });
  const isFollowing = !!id && !!followed.data?.includes(id);
  const toggle = useMutation({
    mutationFn: () => api(`/api/follows/${id}`, { method: isFollowing ? "DELETE" : "PUT" }),
    onSettled: () => {
      for (const queryKey of [["follow-ids"], ["follows"], ["releases"]]) void client.invalidateQueries({ queryKey });
    },
  });

  if (artist.isError) return <p className="form-error" role="alert">{artist.error.message}</p>;
  if (!artist.data) return <p role="status">Cargando…</p>;
  const { name, bio, source, songs, photo_url: photo, links } = artist.data;

  return (
    <>
      {photo && <img className="artist-photo" src={photo} alt={`Foto de ${name}`} />}
      <h1 className="page-title">{name}</h1>
      <p className="muted">{source === "jamendo" ? "Artista de Jamendo" : "Compositor de MELOXO"}</p>
      {bio && <p>{bio}</p>}
      <ArtistLinks links={links} />
      <div className="row-actions">
        <button className={isFollowing ? "ghost" : "primary"} type="button" disabled={toggle.isPending} aria-pressed={isFollowing} onClick={() => toggle.mutate()}>
          {isFollowing ? "Siguiendo" : "Seguir"}
        </button>
      </div>
      <ul className="songs">
        {songs.map((song, index) => <SongRow key={song.id} song={song} onPlay={() => play(songs, index)} />)}
      </ul>
    </>
  );
}
