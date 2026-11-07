import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Page, Song } from "../api/types";
import { SongRow } from "../components/SongRow";
import { usePlayer } from "../player/PlayerProvider";

const SIZE = 30;

export function Search() {
  const { play } = usePlayer();
  const [params, setParams] = useSearchParams();
  const genres = useQuery({ queryKey: ["genres"], queryFn: () => api<string[]>("/api/genres") });
  const filters = params.toString();

  const results = useInfiniteQuery({
    queryKey: ["search", filters],
    initialPageParam: 1,
    queryFn: ({ pageParam }) => {
      const query = new URLSearchParams(params);
      query.set("page", String(pageParam));
      query.set("size", String(SIZE));
      return api<Page<Song>>(`/api/songs?${query}`);
    },
    getNextPageParam: (last) => (last.page * last.size < last.total ? last.page + 1 : undefined),
  });

  function setFilter(name: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    setParams(next, { replace: true });
  }

  const songs = results.data?.pages.flatMap((page) => page.items) ?? [];
  const total = results.data?.pages[0]?.total ?? 0;

  return (
    <>
      <h1 className="page-title">Buscar</h1>
      <div className="filters">
        <label>
          Género
          <select value={params.get("genre") ?? ""} onChange={(e) => setFilter("genre", e.target.value)}>
            <option value="">Todos</option>
            {genres.data?.map((genre) => <option key={genre} value={genre}>{genre}</option>)}
          </select>
        </label>
        <label>
          Fuente
          <select value={params.get("source") ?? ""} onChange={(e) => setFilter("source", e.target.value)}>
            <option value="">Todas</option>
            <option value="jamendo">Jamendo</option>
            <option value="local">Compositores de MELOXO</option>
          </select>
        </label>
        <label>
          Artista
          <input type="text" value={params.get("artist") ?? ""} onChange={(e) => setFilter("artist", e.target.value)} />
        </label>
        <label>
          Etiqueta
          <input type="text" value={params.get("tag") ?? ""} onChange={(e) => setFilter("tag", e.target.value)} />
        </label>
      </div>
      {results.isError && <p className="form-error" role="alert">{results.error.message}</p>}
      {results.isSuccess && (
        <p className="muted" role="status">{total === 1 ? "1 resultado" : `${total} resultados`}</p>
      )}
      <ul className="songs">
        {songs.map((song, index) => <SongRow key={song.id} song={song} onPlay={() => play(songs, index)} />)}
      </ul>
      {results.hasNextPage && (
        <button className="ghost" type="button" disabled={results.isFetchingNextPage} onClick={() => void results.fetchNextPage()}>
          Cargar más
        </button>
      )}
    </>
  );
}
