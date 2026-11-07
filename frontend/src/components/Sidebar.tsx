import { useState } from "react";
import { Link } from "react-router-dom";
import { useFollows, usePendingInvites, usePlaylists, useTapes } from "../api/queries";
import { Icon } from "./Icon";
import { tapeHex } from "./tapeColors";

type Tab = "tapes" | "playlists" | "artists";

const tabs: { id: Tab; label: string }[] = [
  { id: "tapes", label: "Casetes" },
  { id: "playlists", label: "Playlists" },
  { id: "artists", label: "Artistas" },
];

function Tapes() {
  const tapes = useTapes();
  const invites = usePendingInvites();
  return (
    <>
      {tapes.data?.map((tape) => (
        <Link className="lib-row" key={tape.id} to={`/tapes/${tape.id}`}>
          <span className="swatch" style={{ background: tapeHex(tape.color) }} />
          <span>
            <b>{tape.title}</b>
            <small>{tape.track_count} de {tape.max_tracks} · {tape.member_count === 1 ? "1 persona" : `${tape.member_count} personas`}</small>
          </span>
        </Link>
      ))}
      {invites.data?.map((invite) => (
        <Link className="lib-row" key={invite.invite_id} to="/library">
          <span className="swatch swatch-paper" />
          <span>
            <b>{invite.title}</b>
            <small>Invitación pendiente</small>
          </span>
        </Link>
      ))}
    </>
  );
}

function Playlists() {
  const playlists = usePlaylists();
  return (
    <>
      {playlists.data?.map((playlist) => (
        <Link className="lib-row" key={playlist.id} to={`/playlists/${playlist.id}`}>
          <span className="swatch swatch-paper" />
          <span><b>{playlist.name}</b></span>
        </Link>
      ))}
    </>
  );
}

function Artists() {
  const follows = useFollows();
  return (
    <>
      {follows.data?.map((artist) => (
        <Link className="lib-row" key={artist.id} to={`/artists/${artist.id}`}>
          <span className="swatch swatch-teal" />
          <span><b>{artist.name}</b></span>
        </Link>
      ))}
    </>
  );
}

export function Sidebar() {
  const [tab, setTab] = useState<Tab>("tapes");
  return (
    <>
      <Link className="primary create" to="/tapes/new"><Icon name="plus" />Crear casete</Link>
      <div className="pills" role="group" aria-label="Filtrar biblioteca">
        {tabs.map((item) => (
          <button key={item.id} type="button" aria-pressed={tab === item.id} onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="lib">
        {tab === "tapes" && <Tapes />}
        {tab === "playlists" && <Playlists />}
        {tab === "artists" && <Artists />}
      </div>
    </>
  );
}
