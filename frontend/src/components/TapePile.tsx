import { Link } from "react-router-dom";
import type { TapeSummary } from "../api/types";
import { Tape } from "./Tape";

const tilts = [-4, 3, -2, 5, -3];
const offsets = [0, 10, -6, 6, -2];

export function TapePile({ tapes }: { tapes: TapeSummary[] }) {
  return (
    <ul className="pile">
      {tapes.map((tape, index) => (
        <li key={tape.id} style={{ zIndex: tapes.length - index, "--tilt": `${tilts[index % 5]}deg`, "--lift": `${offsets[index % 5]}px` } as React.CSSProperties}>
          <Link to={`/tapes/${tape.id}`} aria-label={`${tape.title}, ${tape.track_count} pistas`}>
            <Tape title={tape.title} color={tape.color} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
