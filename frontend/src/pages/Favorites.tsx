import { useFavorites } from "../api/queries";
import { SongRow } from "../components/SongRow";
import { usePlayer } from "../player/PlayerProvider";

export function Favorites() {
  const { play } = usePlayer();
  const favorites = useFavorites();
  const songs = favorites.data?.items ?? [];
  return (
    <>
      <h1 className="page-title">Favoritas</h1>
      {favorites.isSuccess && !songs.length && <p className="muted">Marca una pista con el corazón y aparecerá aquí.</p>}
      <ul className="songs">
        {songs.map((song, index) => <SongRow key={song.id} song={song} onPlay={() => play(songs, index)} />)}
      </ul>
    </>
  );
}
