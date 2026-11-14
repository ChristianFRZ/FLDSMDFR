import { Link } from "react-router-dom";
import type { TapeSummary } from "../api/types";
import { orderLibrary } from "./libraryOrder";
import { useLibraryPrefs } from "./libraryPrefs";
import { PinButton } from "./PinButton";
import { Tape } from "./Tape";

const tilts = [-4, 3, -2, 5, -3];
const offsets = [0, 10, -6, 6, -2];

export function TapePile({ tapes }: { tapes: TapeSummary[] }) {
  const { pinned, sort } = useLibraryPrefs();
  const ordered = orderLibrary(tapes, pinned, sort, { id: (tape) => tape.id, name: (tape) => tape.title });
  return (
    <ul className="pile">
      {ordered.map((tape, index) => (
        <li key={tape.id} style={{ zIndex: ordered.length - index, "--tilt": `${tilts[index % 5]}deg`, "--lift": `${offsets[index % 5]}px` } as React.CSSProperties}>
          <Link to={`/tapes/${tape.id}`} aria-label={`${tape.title}, ${tape.track_count} pistas`}>
            <Tape title={tape.title} color={tape.color} />
          </Link>
          <PinButton id={tape.id} label={tape.title} />
        </li>
      ))}
    </ul>
  );
}
