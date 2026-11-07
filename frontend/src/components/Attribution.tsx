import type { Song } from "../api/types";

/** La licencia no se muestra aquí: la de cada pista de Jamendo se consulta en su página, enlazada desde el crédito. */
export function Attribution({ song }: { song: Song }) {
  if (song.source !== "jamendo") {
    return <small>{song.artist} · vía MELOXO</small>;
  }
  return (
    <small className="credit">
      {song.artist} · vía{" "}
      <a href={song.jamendo_url ?? "https://www.jamendo.com"} target="_blank" rel="noreferrer">Jamendo</a>
    </small>
  );
}
