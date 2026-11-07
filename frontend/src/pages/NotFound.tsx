import { Link } from "react-router-dom";
import { Note } from "../components/Note";

export function NotFound() {
  return (
    <Note tape className="empty-note">
      Esta cinta no existe.
      <Link to="/">Volver a Inicio</Link>
    </Note>
  );
}
