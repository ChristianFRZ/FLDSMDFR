import { useState } from "react";
import type { TapeTrack } from "../api/types";
import { Icon } from "./Icon";
import { Note } from "./Note";
import { SongRow } from "./SongRow";

type Props = {
  side: "A" | "B";
  tracks: TapeTrack[];
  total: number;
  busy: boolean;
  onPlay: (track: TapeTrack) => void;
  onMove: (track: TapeTrack, to: number) => void;
  onRemove: (track: TapeTrack) => void;
};

function Remove({ track, onRemove }: { track: TapeTrack; onRemove: Props["onRemove"] }) {
  const [asking, setAsking] = useState(false);
  if (asking) {
    return (
      <span className="confirm">
        <button className="ghost danger" type="button" onClick={() => onRemove(track)}>Quitar</button>
        <button className="ghost" type="button" onClick={() => setAsking(false)}>No</button>
      </span>
    );
  }
  return (
    <button className="plain" type="button" aria-label={`Quitar ${track.song.title}`} onClick={() => setAsking(true)}>
      <Icon name="trash" />
    </button>
  );
}

export function TapeSide({ side, tracks, total, busy, onPlay, onMove, onRemove }: Props) {
  const [dragging, setDragging] = useState<TapeTrack | null>(null);
  const heading = `tape-side-${side}`;
  return (
    <section className="tape-side" role="region" aria-labelledby={heading}>
      <h2 id={heading}>Lado {side}</h2>
      {tracks.length ? (
        <ol className="tracks">
          {tracks.map((track) => (
            <li
              key={track.id}
              draggable={!busy}
              onDragStart={() => setDragging(track)}
              onDragEnd={() => setDragging(null)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                if (dragging && dragging.id !== track.id) onMove(dragging, track.position);
                setDragging(null);
              }}
            >
              <SongRow
                as="div"
                song={track.song}
                onPlay={() => onPlay(track)}
                actions={
                  <>
                    <button
                      className="plain"
                      type="button"
                      aria-label={`Subir ${track.song.title}`}
                      disabled={busy || track.position === 1}
                      onClick={() => onMove(track, track.position - 1)}
                    >
                      <Icon name="up" />
                    </button>
                    <button
                      className="plain"
                      type="button"
                      aria-label={`Bajar ${track.song.title}`}
                      disabled={busy || track.position === total}
                      onClick={() => onMove(track, track.position + 1)}
                    >
                      <Icon name="down" />
                    </button>
                    {track.can_remove && <Remove track={track} onRemove={onRemove} />}
                  </>
                }
              />
              {track.dedication && (
                <Note className="track-note">
                  {track.dedication}
                  <small>De {track.added_by_name}</small>
                </Note>
              )}
            </li>
          ))}
        </ol>
      ) : (
        <p className="muted">Este lado sigue en blanco.</p>
      )}
    </section>
  );
}
