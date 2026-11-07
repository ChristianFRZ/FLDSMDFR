import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { HistoryItem, Page, Song } from "../api/types";
import { SongRow } from "../components/SongRow";
import { usePlayer } from "../player/PlayerProvider";

export function History() {
  const { play } = usePlayer();
  const history = useQuery({
    queryKey: ["history"],
    queryFn: () => api<Page<HistoryItem>>("/api/playbacks/history?size=100"),
  });
  const items = (history.data?.items ?? []).filter((item): item is HistoryItem & { song: Song } => item.song !== null);
  return (
    <>
      <h1 className="page-title">Historial</h1>
      {history.isSuccess && !items.length && <p className="muted">Lo que escuches más de 10 segundos queda aquí.</p>}
      <ul className="songs">
        {items.map((item) => <SongRow key={item.playback_id} song={item.song} onPlay={() => play([item.song])} />)}
      </ul>
    </>
  );
}
