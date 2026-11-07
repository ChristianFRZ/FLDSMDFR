import { Link } from "react-router-dom";
import { Attribution } from "../components/Attribution";
import { Note } from "../components/Note";
import { Tape } from "../components/Tape";
import { usePlayer } from "./PlayerProvider";

export function NowPanel() {
  const { current, context, queue, jump } = usePlayer();
  if (!current) {
    return (
      <>
        <h3 className="now-title">Sonando</h3>
        <Tape title="Nada todavía" color="cobalt" tilt={-3} className="now-tape" />
        <small>Cuando pongas algo, aparece aquí.</small>
      </>
    );
  }
  return (
    <>
      <h3 className="now-title">{current.side ? `Sonando · Lado ${current.side}` : "Sonando"}</h3>
      {context ? (
        <Link to={context.href} aria-label={`Abrir ${context.title}`}>
          <Tape title={context.title} color={context.color} tilt={-3} className="now-tape" />
        </Link>
      ) : (
        <Tape title={current.title} color="pink" tilt={-3} className="now-tape" />
      )}
      <b className="now-song">{current.title}</b>
      <Attribution song={current} />
      {current.dedication && (
        <Note tape className="now-note">
          {current.dedication}
          <small>Dedicatoria de {current.dedicatedBy}</small>
        </Note>
      )}
      {queue.length > 0 && (
        <div className="now-next">
          <small>Sigue</small>
          <ol>
            {queue.slice(0, 3).map((song, offset) => (
              <li key={`${song.id}-${offset}`}>
                <button type="button" onClick={() => jump(offset)}>{song.title}</button>
              </li>
            ))}
          </ol>
        </div>
      )}
    </>
  );
}
