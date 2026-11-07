import type { ReactNode } from "react";
import type { Song } from "../api/types";
import { clock } from "../player/format";
import { useAddSong } from "./AddSong";
import { Attribution } from "./Attribution";
import { Cover } from "./Cover";
import { Icon } from "./Icon";

type Props = { song: Song; onPlay: () => void; actions?: ReactNode; as?: "li" | "div" };

export function SongRow({ song, onPlay, actions, as: Tag = "li" }: Props) {
  const addSong = useAddSong();
  return (
    <Tag className={song.available ? "song" : "song song-off"}>
      <button
        className="song-play"
        type="button"
        aria-label={`Reproducir ${song.title}`}
        disabled={!song.available}
        onClick={onPlay}
      >
        <Cover id={song.id} url={song.cover_url} className="cover-row" />
        <span className="song-play-icon"><Icon name="play" filled /></span>
      </button>
      <div className="song-text">
        <b>{song.title}</b>
        {song.available ? <Attribution song={song} /> : <small className="tag-off">No disponible</small>}
      </div>
      <span className="song-time">{clock(song.duration)}</span>
      {song.available && (
        <button className="plain" type="button" aria-label={`Agregar ${song.title} a un casete o playlist`} onClick={() => addSong(song)}>
          <Icon name="plus" />
        </button>
      )}
      {actions}
    </Tag>
  );
}
